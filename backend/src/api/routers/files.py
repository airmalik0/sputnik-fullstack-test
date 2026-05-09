"""File endpoints.

The router is a thin shell: parse input, delegate to a service, return a
schema. Anything more elaborate (validation across fields, multi-step
orchestration) belongs in the service.

Two non-trivial pieces live here and not in the service:

  * Transaction boundary. The router receives a session via DI and is
    responsible for `await session.commit()` after a successful mutation.
    Putting it here (and not in the service) keeps services agnostic of
    request scope.
  * Background-job dispatch. Enqueueing the Celery task is a transport
    concern — the service does not know that file processing is async.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_file_service,
    get_request_session,
)
from src.api.schemas import FileItem, FileUpdate
from src.services.file_service import FileService
from src.tasks import process_file


router = APIRouter(prefix="/files", tags=["files"])


# Tuned to balance memory pressure with syscall overhead. 64 KiB is the
# common sweet spot for SSD throughput and matches what the tempfile
# implementation in storage uses internally.
_UPLOAD_CHUNK_SIZE = 64 * 1024


async def _stream_upload(upload: UploadFile) -> AsyncIterator[bytes]:
    while chunk := await upload.read(_UPLOAD_CHUNK_SIZE):
        yield chunk


@router.get("", response_model=list[FileItem])
async def list_files(
    file_service: FileService = Depends(get_file_service),
) -> list[FileItem]:
    files = await file_service.list_files()
    return [FileItem.model_validate(f) for f in files]


@router.post("", response_model=FileItem, status_code=201)
async def create_file(
    title: str = Form(...),
    file: UploadFile = File(...),
    file_service: FileService = Depends(get_file_service),
    session: AsyncSession = Depends(get_request_session),
) -> FileItem:
    created = await file_service.create_file(
        title=title,
        original_name=file.filename,
        content_type=file.content_type,
        stream=_stream_upload(file),
    )
    # Commit before enqueueing the background task — the worker reads the
    # row by id, so the row must be visible to other connections first.
    # Enqueueing before commit would race with the worker.
    await session.commit()
    process_file.delay(created.id)
    return FileItem.model_validate(created)


@router.get("/{file_id}", response_model=FileItem)
async def get_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service),
) -> FileItem:
    file = await file_service.get_file(file_id)
    return FileItem.model_validate(file)


@router.patch("/{file_id}", response_model=FileItem)
async def update_file(
    file_id: str,
    payload: FileUpdate,
    file_service: FileService = Depends(get_file_service),
    session: AsyncSession = Depends(get_request_session),
) -> FileItem:
    file = await file_service.update_title(file_id=file_id, title=payload.title)
    await session.commit()
    return FileItem.model_validate(file)


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service),
) -> FileResponse:
    file, path = await file_service.open_for_download(file_id)
    return FileResponse(
        path=path,
        media_type=file.mime_type,
        filename=file.original_name,
    )


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service),
    session: AsyncSession = Depends(get_request_session),
) -> None:
    await file_service.delete_file(file_id)
    await session.commit()
