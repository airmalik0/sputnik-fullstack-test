"""Local-filesystem storage with atomic writes.

The atomicity is the load-bearing part. The original implementation called
`stored_path.write_bytes(content)` and then committed to the DB. If the
process died between the write and the commit, the on-disk file became an
orphan — present on disk, absent from the index.

This implementation uses the standard 'write to a temp file in the same
directory, fsync, then os.replace' recipe. `os.replace` is atomic on POSIX
filesystems within a single mount point, so the final filename either
points at the fully-written file or doesn't exist at all. We further
guarantee that the FILE is durable before rename via fsync, and the
DIRECTORY entry is durable via fsync on the directory after rename.

Even with this, the orphan-file problem is not fully eliminated — the
service first calls `save_stream`, then commits to the DB; a crash between
those two steps leaves an orphan. That is acceptable: an orphan file is
strictly less harmful than a missing file (the index would point at
nothing). We periodically reconcile via a separate cleanup job (out of
scope for this MVP, called out in the README).
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

from src.storage.base import FileStorage


class LocalFileStorage(FileStorage):
    def __init__(self, root: Path) -> None:
        self._root = root
        # Created lazily here rather than at module import time, so tests
        # that point at a temp dir don't get a stale `storage/files`
        # directory created in the source tree.
        self._root.mkdir(parents=True, exist_ok=True)

    def path(self, stored_name: str) -> Path:
        return self._root / stored_name

    def exists(self, stored_name: str) -> bool:
        return self.path(stored_name).exists()

    async def save_stream(
        self, stream: AsyncIterator[bytes], stored_name: str
    ) -> int:
        target = self.path(stored_name)
        # Temp file lives in the same directory as the target so that
        # os.replace is a rename within one filesystem (atomic).
        fd, temp_path_str = tempfile.mkstemp(
            prefix=".tmp-", suffix=stored_name, dir=str(self._root)
        )
        temp_path = Path(temp_path_str)
        bytes_written = 0
        try:
            try:
                async for chunk in stream:
                    if not chunk:
                        continue
                    bytes_written += len(chunk)
                    await asyncio.to_thread(os.write, fd, chunk)
                # fsync the file before rename: the rename is atomic, but
                # without fsync the file's data may not be durable when the
                # rename becomes visible. Pulling the plug here would
                # otherwise produce a zero-length file under the final name.
                await asyncio.to_thread(os.fsync, fd)
            finally:
                os.close(fd)
            await asyncio.to_thread(os.replace, temp_path, target)
            # Make the directory entry durable too.
            dir_fd = await asyncio.to_thread(os.open, str(self._root), os.O_RDONLY)
            try:
                await asyncio.to_thread(os.fsync, dir_fd)
            finally:
                await asyncio.to_thread(os.close, dir_fd)
            return bytes_written
        except BaseException:
            # Clean up the temp file on any failure (including cancellation)
            # so we never leak partial uploads under .tmp-* names.
            await asyncio.to_thread(_unlink_silent, temp_path)
            raise

    async def delete(self, stored_name: str) -> None:
        await asyncio.to_thread(_unlink_silent, self.path(stored_name))


def _unlink_silent(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
