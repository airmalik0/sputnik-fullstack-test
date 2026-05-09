"""End-to-end API tests via httpx ASGITransport.

These exist to catch the class of bug that the unit tests can't see —
mistakes that only show up when FastAPI assembles the dependency graph
for a real request. The first such bug we shipped was a `lru_cache`
that received a `Settings` object as its key (Pydantic models aren't
hashable), which only blew up at request time. A test like this would
have failed before push.

Strategy:

  * SQLite in-memory for the database. Schema is created from
    SQLAlchemy metadata, no Alembic round trip needed.
  * In-memory FileStorage so uploads don't touch disk.
  * `process_file.delay` is monkeypatched to a no-op — the test runs
    without Redis, and we don't care about Celery here. The Celery
    task is exercised by tests against ScanService / MetadataExtractor
    directly.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.api.dependencies import get_db_session, get_storage
from src.app import create_app
from src.domain.models import Base
from tests.fakes import InMemoryStorage


@pytest.fixture
async def client(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    storage = InMemoryStorage()

    # No-op for Celery dispatch: we test the HTTP surface, not the worker.
    monkeypatch.setattr(
        "src.api.routers.files.process_file.delay", lambda *a, **kw: None
    )

    async def override_session():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_storage] = lambda: storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await engine.dispose()


async def test_files_list_starts_empty(client: AsyncClient):
    response = await client.get("/files")
    assert response.status_code == 200
    assert response.json() == []


async def test_alerts_list_starts_empty(client: AsyncClient):
    response = await client.get("/alerts")
    assert response.status_code == 200
    assert response.json() == []


async def test_create_file_returns_201_with_full_dto(client: AsyncClient):
    files = {"file": ("hello.txt", b"hello world", "text/plain")}
    response = await client.post("/files", files=files, data={"title": "Hello"})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Hello"
    assert body["original_name"] == "hello.txt"
    assert body["mime_type"] == "text/plain"
    assert body["size"] == 11
    assert body["processing_status"] == "uploaded"
    # The DTO does not expose sha256 (kept internal), but it must
    # carry every field declared in api/schemas.py.
    for field in (
        "id",
        "scan_status",
        "scan_details",
        "metadata_json",
        "requires_attention",
        "created_at",
        "updated_at",
    ):
        assert field in body


async def test_get_missing_file_returns_404(client: AsyncClient):
    response = await client.get("/files/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json() == {"detail": "File not found"}


async def test_empty_upload_returns_400(client: AsyncClient):
    files = {"file": ("empty.txt", b"", "text/plain")}
    response = await client.post("/files", files=files, data={"title": "Empty"})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


async def test_full_lifecycle_create_get_update_delete(client: AsyncClient):
    create = await client.post(
        "/files",
        files={"file": ("doc.txt", b"some content", "text/plain")},
        data={"title": "Original"},
    )
    file_id = create.json()["id"]

    fetched = await client.get(f"/files/{file_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Original"

    updated = await client.patch(
        f"/files/{file_id}", json={"title": "Renamed"}
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Renamed"

    deleted = await client.delete(f"/files/{file_id}")
    assert deleted.status_code == 204

    gone = await client.get(f"/files/{file_id}")
    assert gone.status_code == 404


async def test_listing_after_creates_returns_descending_order(client: AsyncClient):
    # Created in order A, B; expected in list order B, A (newest first).
    # We pause between creates because SQLite's now() has only second
    # precision — without the gap two inserts can share a timestamp and
    # the tiebreaker (id, a UUID string) is not chronological.
    import asyncio

    for title in ("A", "B"):
        r = await client.post(
            "/files",
            files={"file": ("x.txt", b"x", "text/plain")},
            data={"title": title},
        )
        assert r.status_code == 201
        await asyncio.sleep(1.05)

    response = await client.get("/files")
    titles = [item["title"] for item in response.json()]
    assert titles == ["B", "A"]
