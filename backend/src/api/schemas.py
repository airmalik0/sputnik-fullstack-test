"""Request and response schemas exposed over HTTP.

Why these are separate from the ORM models:

  * The API contract is a stable shape; the DB schema can evolve under it.
  * Pydantic validation is a feature only at the boundary — services
    consume already-validated values, and the type system inside the
    domain stays free of validation noise.

Schemas mirror the original API exactly (same fields, same names, same
JSON shapes). The only intentional change is that status fields use
typed Enums, which makes the OpenAPI document more precise without
altering the wire format.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.domain.enums import AlertLevel, ProcessingStatus, ScanStatus


class FileItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    original_name: str
    mime_type: str
    size: int
    processing_status: ProcessingStatus
    scan_status: ScanStatus | None
    scan_details: str | None
    metadata_json: dict | None
    requires_attention: bool
    created_at: datetime
    updated_at: datetime


class FileUpdate(BaseModel):
    title: str


class AlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: str
    level: AlertLevel
    message: str
    created_at: datetime
