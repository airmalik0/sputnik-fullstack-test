"""In-memory fakes for tests.

These exist because the real architecture lets us substitute the
infrastructure pieces (storage, repository) with anything that satisfies
the same shape. The fakes keep tests fast (no Postgres, no disk I/O)
and trivially reset between tests (just construct a new one).
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from pathlib import Path

from src.domain.models import Alert, StoredFile
from src.storage.base import StoredObject


class FakeFileRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, StoredFile] = {}

    async def list_all(self) -> list[StoredFile]:
        return list(self._by_id.values())

    async def get(self, file_id: str) -> StoredFile | None:
        return self._by_id.get(file_id)

    def add(self, file: StoredFile) -> None:
        self._by_id[file.id] = file

    async def delete(self, file: StoredFile) -> None:
        self._by_id.pop(file.id, None)


class FakeAlertRepository:
    def __init__(self) -> None:
        self.alerts: list[Alert] = []

    async def list_all(self) -> list[Alert]:
        return list(self.alerts)

    def add(self, alert: Alert) -> None:
        self.alerts.append(alert)


class InMemoryStorage:
    """A FileStorage implementation backed by a dict.

    Mirrors the real semantics that matter for behavioural tests: atomic
    save (either fully present after save or absent on raise), idempotent
    delete, hash + size returned from save.
    """

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}

    async def save_stream(
        self, stream: AsyncIterator[bytes], stored_name: str
    ) -> StoredObject:
        chunks: list[bytes] = []
        async for chunk in stream:
            chunks.append(chunk)
        data = b"".join(chunks)
        self._blobs[stored_name] = data
        return StoredObject(size=len(data), sha256=hashlib.sha256(data).hexdigest())

    async def delete(self, stored_name: str) -> None:
        self._blobs.pop(stored_name, None)

    def exists(self, stored_name: str) -> bool:
        return stored_name in self._blobs

    def path(self, stored_name: str) -> Path:
        # Tests that need a real path should use a tmp_path-backed
        # LocalFileStorage instead. Returning a fake path here would
        # invite subtle bugs.
        raise NotImplementedError("InMemoryStorage has no on-disk path")
