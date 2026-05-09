"""Translate domain exceptions into HTTP responses.

Single source of truth for "what does FileNotFound mean over HTTP?". Every
endpoint benefits from these handlers; nothing has to remember to wrap
service calls in try/except.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status

from src.domain.exceptions import (
    DomainError,
    EmptyFile,
    FileNotFound,
    StoredFileMissing,
)

logger = logging.getLogger(__name__)


def _error(detail: str, code: int) -> JSONResponse:
    # Match FastAPI's default error envelope so existing clients that read
    # `error["detail"]` keep working without changes.
    return JSONResponse(status_code=code, content={"detail": detail})


def _file_not_found_handler(_: Request, exc: FileNotFound) -> JSONResponse:
    return _error("File not found", status.HTTP_404_NOT_FOUND)


def _empty_file_handler(_: Request, exc: EmptyFile) -> JSONResponse:
    return _error(str(exc) or "File is empty", status.HTTP_400_BAD_REQUEST)


def _stored_missing_handler(_: Request, exc: StoredFileMissing) -> JSONResponse:
    # 404 from the user's perspective — they asked for a file we can't
    # serve. Logged at WARNING because it indicates a data integrity issue
    # that should be investigated (DB and storage have diverged).
    logger.warning(
        "Stored file missing on disk", extra={"file_id": exc.file_id}
    )
    return _error("Stored file not found", status.HTTP_404_NOT_FOUND)


def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    # Catch-all for any future DomainError subclasses we haven't mapped
    # explicitly. Logging at ERROR because reaching here means we forgot
    # to write a specific handler.
    logger.exception("Unmapped domain error", exc_info=exc)
    return _error("Internal error", status.HTTP_500_INTERNAL_SERVER_ERROR)


def register_exception_handlers(app: FastAPI) -> None:
    # Order matters: more specific subclasses must come before DomainError
    # so the catch-all doesn't shadow them. FastAPI checks handlers
    # against `isinstance`, picking the first registered match.
    app.add_exception_handler(FileNotFound, _file_not_found_handler)
    app.add_exception_handler(EmptyFile, _empty_file_handler)
    app.add_exception_handler(StoredFileMissing, _stored_missing_handler)
    app.add_exception_handler(DomainError, _domain_error_handler)
