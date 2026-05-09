"""Celery application factory.

A separate module from `process_file` so that other tasks (a future
periodic janitor for orphaned blobs, a manual re-scan command) can
register themselves without circular imports.
"""

from __future__ import annotations

from celery import Celery

from src.core.config import get_settings
from src.core.logging import configure_logging


def _build_celery() -> Celery:
    configure_logging()
    settings = get_settings()
    return Celery(
        "file_tasks",
        broker=settings.celery_broker_url,
        backend=settings.celery_broker_url,
    )


celery_app = _build_celery()

# Register task modules. The import has to happen AFTER celery_app is
# built — process_file imports celery_app from this module, and only the
# attribute already exists in our namespace. Wrapped in noqa because
# F401 would otherwise flag the unused-looking import.
from src.tasks import process_file  # noqa: E402, F401
