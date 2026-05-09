"""Logging bootstrap.

Centralised so we can later swap to structured JSON logging (e.g. for
shipping to Loki/ELK) without hunting down `logging.basicConfig` calls.
"""

import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """Idempotent logging setup. Safe to call from both uvicorn and Celery."""
    root = logging.getLogger()
    if root.handlers:
        # Already configured (typically by uvicorn / Celery). Don't double-add
        # handlers — that would duplicate every log line.
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(level)
