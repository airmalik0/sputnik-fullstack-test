"""File lifecycle service.

Owns the rules for creating, reading, updating and deleting files:

  * The order in which the binary write and the DB row are committed (and
    the cleanup if either fails).
  * Generation of identifiers and stored names.
  * Mime-type fallback when the client did not send Content-Type.

Important contract: the service raises domain exceptions, never
HTTPException. Translation to HTTP is the API layer's job.
"""

from __future__ import annotations

import mimetypes
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

from src.domain.enums import ProcessingStatus
from src.domain.exceptions import EmptyFile, FileNotFound, StoredFileMissing
from src.domain.models import StoredFile
from src.repositories.file_repository import FileRepository
from src.storage.base import FileStorage


class FileService:
    def __init__(
        self,
        repository: FileRepository,
        storage: FileStorage,
    ) -> None:
        self._repository = repository
        self._storage = storage

    async def list_files(self) -> list[StoredFile]:
        return await self._repository.list_all()

    async def get_file(self, file_id: str) -> StoredFile:
        file = await self._repository.get(file_id)
        if file is None:
            raise FileNotFound(file_id)
        return file

    async def create_file(
        self,
        *,
        title: str,
        original_name: str | None,
        content_type: str | None,
        stream: AsyncIterator[bytes],
    ) -> StoredFile:
        """Persist an upload to storage, then to the database.

        Order of operations is deliberate:

          1. Write to storage atomically. If this fails, nothing was
             persisted anywhere and the caller gets the exception.
          2. Add the DB row in the caller-supplied transaction. The caller
             commits.
          3. If anything between steps 1 and 2 raises, delete the on-disk
             blob to avoid an orphan.

        We do NOT support resuming partial uploads — each call is a fresh
        write under a freshly-generated stored_name.
        """

        file_id = str(uuid4())
        # Preserve the original suffix for stored_name so disk introspection
        # tools (file managers, antivirus) can guess the format.
        suffix = Path(original_name or "").suffix
        stored_name = f"{file_id}{suffix}"

        # `storage.save_stream` raises on I/O error; nothing has been
        # written to the DB yet, so we propagate as-is.
        stored = await self._storage.save_stream(stream, stored_name)

        if stored.size == 0:
            # Mirrors the original 'File is empty' guard, but applied after
            # writing — necessary for streaming uploads where we don't know
            # the size until we've consumed the stream.
            await self._storage.delete(stored_name)
            raise EmptyFile("File is empty")

        # `mimetypes.guess_type` works on the filename alone; for content-
        # based detection we'd need libmagic, which is overkill for the MVP.
        # Falling back to octet-stream matches the original behaviour and
        # keeps the API contract identical.
        resolved_mime = (
            content_type
            or mimetypes.guess_type(stored_name)[0]
            or "application/octet-stream"
        )

        file = StoredFile(
            id=file_id,
            title=title,
            original_name=original_name or stored_name,
            stored_name=stored_name,
            mime_type=resolved_mime,
            size=stored.size,
            sha256=stored.sha256,
            processing_status=ProcessingStatus.UPLOADED.value,
        )
        try:
            self._repository.add(file)
        except Exception:
            # Persist nothing if the in-memory add itself fails (it
            # shouldn't, but defensive against future repository changes).
            await self._storage.delete(stored_name)
            raise
        return file

    async def update_title(self, file_id: str, title: str) -> StoredFile:
        file = await self.get_file(file_id)
        file.title = title
        return file

    async def delete_file(self, file_id: str) -> None:
        """Delete the DB row, then the on-disk blob.

        This order is intentional: an orphaned file (DB row gone, blob
        present) is recoverable by a janitor job; an orphaned DB row
        (record present, blob gone) is a 404 every time the user tries to
        download. Always prefer the recoverable failure mode.
        """
        file = await self.get_file(file_id)
        stored_name = file.stored_name
        await self._repository.delete(file)
        # The caller's transaction commits after this method returns;
        # blob deletion happens immediately. If the commit fails, we have
        # an on-disk orphan — picked up by the periodic cleanup job (out
        # of scope for this MVP). If the blob deletion fails, the commit
        # still proceeds, which is the safe direction.
        await self._storage.delete(stored_name)

    async def open_for_download(self, file_id: str) -> tuple[StoredFile, Path]:
        """Resolve the storage path for a download.

        Tightly coupled to local storage by design — see
        `FileStorage.path`. If we ever move to S3, this method gets
        replaced with one that returns a presigned URL and the download
        endpoint changes shape accordingly.
        """
        file = await self.get_file(file_id)
        if not self._storage.exists(file.stored_name):
            raise StoredFileMissing(file.id, file.stored_name)
        return file, self._storage.path(file.stored_name)
