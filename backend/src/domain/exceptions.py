"""Domain exceptions.

Services raise these instead of `fastapi.HTTPException`. Two reasons:

  1. Services must remain reusable from non-HTTP contexts (Celery tasks,
     scripts, tests). HTTPException leaking out of a service is a category
     error there — the worker has nothing to do with HTTP status codes.
  2. The translation from a domain failure to an HTTP response is policy,
     not logic. It belongs in `api/exception_handlers.py`, where one place
     decides "FileNotFound → 404" for every endpoint at once.
"""


class DomainError(Exception):
    """Base class for all domain-level failures."""


class FileNotFound(DomainError):
    def __init__(self, file_id: str) -> None:
        super().__init__(f"File {file_id!r} not found")
        self.file_id = file_id


class EmptyFile(DomainError):
    """Raised when a client uploads a zero-byte file."""


class StoredFileMissing(DomainError):
    """The DB record exists, but the file is missing on disk.

    Distinct from `FileNotFound` because the resolution is different: a
    missing DB row is a 404 to the user, while a missing on-disk file is a
    server-side data integrity issue — usually a 404 still, but it warrants
    logging at WARNING level.
    """

    def __init__(self, file_id: str, stored_name: str) -> None:
        super().__init__(
            f"Stored file for {file_id!r} not found on disk: {stored_name!r}"
        )
        self.file_id = file_id
        self.stored_name = stored_name
