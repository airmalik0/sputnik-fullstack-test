"""File persistence access.

A repository is intentionally narrow — it doesn't decide what to do when a
record is missing (that's policy, owned by services), and it doesn't commit
(that's a transactional concern, owned by services and tasks).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import StoredFile


class FileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[StoredFile]:
        # Tiebreak on `id` so two rows created in the same millisecond
        # come back in a stable order — without this the test suite is
        # flaky on SQLite (which has whole-second precision for now()).
        result = await self._session.execute(
            select(StoredFile).order_by(
                StoredFile.created_at.desc(), StoredFile.id.desc()
            )
        )
        return list(result.scalars().all())

    async def get(self, file_id: str) -> StoredFile | None:
        return await self._session.get(StoredFile, file_id)

    def add(self, file: StoredFile) -> None:
        # Sync method: SQLAlchemy's `Session.add` is not awaitable. The DB
        # round-trip happens at flush/commit time, owned by the caller.
        self._session.add(file)

    async def delete(self, file: StoredFile) -> None:
        await self._session.delete(file)
