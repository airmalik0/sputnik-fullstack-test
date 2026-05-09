"""FileService behavioural tests.

These verify the contract that the rest of the system relies on:
  * a successful upload persists a row AND a blob;
  * a 0-byte upload raises EmptyFile and does not leak a blob;
  * delete removes both row and blob;
  * download resolution surfaces StoredFileMissing if the blob is gone.

The service is exercised against in-memory fakes — the same FileService
class the production app uses.
"""

import hashlib

import pytest

from src.domain.exceptions import EmptyFile, FileNotFound, StoredFileMissing
from src.services.file_service import FileService
from tests.fakes import FakeFileRepository, InMemoryStorage


async def _aiter_chunks(*chunks: bytes):
    for c in chunks:
        yield c


def _service() -> tuple[FileService, FakeFileRepository, InMemoryStorage]:
    repo = FakeFileRepository()
    storage = InMemoryStorage()
    return FileService(repository=repo, storage=storage), repo, storage


async def test_create_persists_row_and_blob():
    svc, repo, storage = _service()
    file = await svc.create_file(
        title="report",
        original_name="report.txt",
        content_type="text/plain",
        stream=_aiter_chunks(b"hello", b" ", b"world"),
    )
    assert file.size == 11
    assert file.sha256 == hashlib.sha256(b"hello world").hexdigest()
    assert file.processing_status == "uploaded"
    # Row visible to the same repo (same session in the production
    # transaction).
    assert (await repo.get(file.id)) is file
    # Blob landed under the stored_name carved from the uuid + suffix.
    assert storage.exists(file.stored_name)
    assert file.stored_name.endswith(".txt")


async def test_create_empty_file_rejects_and_cleans_blob():
    svc, repo, storage = _service()
    with pytest.raises(EmptyFile):
        await svc.create_file(
            title="x",
            original_name="x.txt",
            content_type="text/plain",
            stream=_aiter_chunks(),
        )
    # No row added, no blob retained — the failure mode must be clean,
    # otherwise we'd leak `.tmp-` orphans on every empty upload.
    assert await repo.list_all() == []
    assert not any(True for _ in storage._blobs)  # type: ignore[attr-defined]


async def test_get_missing_raises_file_not_found():
    svc, _, _ = _service()
    with pytest.raises(FileNotFound):
        await svc.get_file("does-not-exist")


async def test_delete_removes_both_row_and_blob():
    svc, repo, storage = _service()
    file = await svc.create_file(
        title="x",
        original_name="x.bin",
        content_type=None,
        stream=_aiter_chunks(b"data"),
    )
    stored_name = file.stored_name

    await svc.delete_file(file.id)

    assert await repo.get(file.id) is None
    assert not storage.exists(stored_name)


async def test_open_for_download_when_blob_missing_raises_stored_missing():
    svc, _, storage = _service()
    file = await svc.create_file(
        title="x",
        original_name="x.bin",
        content_type=None,
        stream=_aiter_chunks(b"data"),
    )
    # Simulate disk-vs-DB divergence: the row exists, the blob doesn't.
    await storage.delete(file.stored_name)

    with pytest.raises(StoredFileMissing):
        await svc.open_for_download(file.id)
