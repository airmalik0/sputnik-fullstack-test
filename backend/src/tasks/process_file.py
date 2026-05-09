"""Single transactional task that processes an uploaded file.

This is the core perf change of the refactor.

The original implementation chained three Celery tasks:

    scan_file_for_threats.delay(file_id)
        -> extract_file_metadata.delay(file_id)
            -> send_file_alert.delay(file_id)

The chain was paid for at every step:

  * 3 round-trips through Redis (one per .delay).
  * 3 fresh sessions, 3 SELECTs by primary key, 3 commits — for the same
    row, doing the same kind of work.
  * A subtle race: scan and extract could overlap if the broker
    redelivered, mutating the same StoredFile under two sessions and
    overwriting each other's fields.

The shape of the problem doesn't justify any of that. The three steps
always run together, are linearly dependent on each other, and only
touch one entity. Collapsing them into a single task with one session:

  * Cuts the broker overhead by ~3x.
  * Cuts DB I/O by the same factor (one SELECT, one commit).
  * Eliminates the cross-task race entirely (one session, one row).
  * Simplifies failure semantics — either the whole pipeline runs or it
    doesn't, which is what the alert behaviour relied on anyway.

Trade-off: we lose per-step retry granularity. Not relevant in practice
because each step here is cheap and idempotent, and the original code
did not exploit per-step retries either."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from celery.utils.log import get_task_logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.db import get_session_factory
from src.domain.enums import AlertLevel, ProcessingStatus, ScanStatus
from src.domain.models import Alert, StoredFile
from src.services.metadata_extractor import MetadataExtractor
from src.services.scan_service import ScanResult, ScanService
from src.storage.local import LocalFileStorage
from src.tasks.celery_app import celery_app

logger = get_task_logger(__name__)

# Single event loop per worker process. Celery's prefork worker is
# synchronous, so each task call needs to bridge into asyncio. Reusing
# one loop keeps the engine's connection pool warm across tasks.
_worker_loop: asyncio.AbstractEventLoop | None = None


def _run_in_worker_loop(coroutine):
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
    return _worker_loop.run_until_complete(coroutine)


def _alert_for(file: StoredFile) -> Alert:
    if file.processing_status == ProcessingStatus.FAILED.value:
        return Alert(
            file_id=file.id,
            level=AlertLevel.CRITICAL.value,
            message="File processing failed",
        )
    if file.requires_attention:
        return Alert(
            file_id=file.id,
            level=AlertLevel.WARNING.value,
            message=f"File requires attention: {file.scan_details}",
        )
    return Alert(
        file_id=file.id,
        level=AlertLevel.INFO.value,
        message="File processed successfully",
    )


def _apply_scan(file: StoredFile, result: ScanResult) -> None:
    file.scan_status = result.status.value
    file.scan_details = result.details
    file.requires_attention = result.requires_attention


async def _process_file(session: AsyncSession, file_id: str) -> None:
    """All three pipeline steps in one transaction.

    The session is supplied by the caller so tests can hand in a
    transactional sandbox; the production path just wires in a fresh
    session per task invocation.
    """
    file = await session.get(StoredFile, file_id)
    if file is None:
        # The row was deleted between enqueue and execution. Nothing to
        # do; we don't treat this as an error because the user-visible
        # outcome (no row, no alert) is consistent with the deletion.
        logger.warning("process_file: %s not found", file_id)
        return

    settings = get_settings()
    storage = LocalFileStorage(settings.storage_dir)
    scanner = ScanService(suspicious_size_bytes=settings.suspicious_size_bytes)
    extractor = MetadataExtractor(text_byte_limit=settings.text_metadata_byte_limit)

    file.processing_status = ProcessingStatus.PROCESSING.value

    scan_result = scanner.scan(
        original_name=file.original_name,
        mime_type=file.mime_type,
        size=file.size,
    )
    _apply_scan(file, scan_result)

    if not storage.exists(file.stored_name):
        # Mirrors the failure path of the original extract step. Captured
        # here as a single explicit branch instead of being implicit in
        # the second task of a chain.
        file.processing_status = ProcessingStatus.FAILED.value
        if file.scan_status is None:
            file.scan_status = ScanStatus.FAILED.value
        file.scan_details = "stored file not found during metadata extraction"
    else:
        file.metadata_json = extractor.extract(file, storage.path(file.stored_name))
        file.processing_status = ProcessingStatus.PROCESSED.value

    session.add(_alert_for(file))
    await session.commit()


@celery_app.task(name="src.tasks.process_file")
def process_file(file_id: str) -> None:
    async def _run() -> None:
        factory = get_session_factory()
        async with factory() as session:
            try:
                await _process_file(session, file_id)
            except Exception:
                await session.rollback()
                # Re-raise so Celery records the failure and applies any
                # configured retry policy. Logging happens at the worker
                # level via Celery's failure hook.
                raise

    _run_in_worker_loop(_run())


# Backwards-compatible alias for any caller still using the original
# task name. The legacy `scan_file_for_threats` chained out to the next
# step; the new task does it all in-process. Removed once every caller
# is migrated.
scan_file_for_threats = process_file
