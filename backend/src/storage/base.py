"""Storage protocol — what every backend must provide.

We model only what services actually need. Adding a method here is a
deliberate decision: every implementation has to satisfy it, and every
caller becomes coupled to it.

The protocol is async because real implementations (S3, GCS) are network
calls; the local-disk implementation is wrapped in `asyncio.to_thread` so
it conforms.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol


class FileStorage(Protocol):
    async def save_stream(
        self, stream: AsyncIterator[bytes], stored_name: str
    ) -> int:
        """Persist a stream of chunks under `stored_name`.

        Returns the total number of bytes written.

        Implementations must be atomic: a partial write must never become
        observable under the final name. Concretely, callers rely on the
        fact that if `save_stream` raises, `exists(stored_name)` is False.
        """
        ...

    async def delete(self, stored_name: str) -> None:
        """Remove the stored object. Idempotent — no error if absent."""
        ...

    def exists(self, stored_name: str) -> bool: ...

    def path(self, stored_name: str) -> Path:
        """Return a local filesystem path.

        Only meaningful for local storage; remote backends should not
        implement this method (or should raise). Used by the download
        endpoint, which serves files via FastAPI's `FileResponse` and
        therefore needs a real path. When migrating to S3 we'd switch the
        download endpoint to redirect to a presigned URL.
        """
        ...
