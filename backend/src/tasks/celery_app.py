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
    app = Celery(
        "file_tasks",
        broker=settings.celery_broker_url,
        backend=settings.celery_broker_url,
    )
    # Autodiscover keeps this file thin: each task module declares itself
    # via the @celery_app.task decorator and Celery picks them up by
    # walking imports of `src.tasks`.
    app.autodiscover_tasks(["src.tasks"], related_name="process_file", force=True)
    return app


celery_app = _build_celery()
