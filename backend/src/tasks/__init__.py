"""Background processing tasks.

This package replaces the original three-step Celery chain
(scan -> metadata -> alert) with a single transactional task. See
`tasks/process_file.py` for the rationale.
"""

from src.tasks.celery_app import celery_app
from src.tasks.process_file import process_file

__all__ = ["celery_app", "process_file"]
