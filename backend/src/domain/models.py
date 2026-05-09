"""SQLAlchemy ORM models.

These describe the on-disk shape of our data. Two design notes:

  * Status columns stay `String` rather than the SQL ENUM type. We map them
    to `domain.enums` values in the application layer. This is a deliberate
    trade-off: VARCHAR is trivially extendable (no ALTER TYPE migrations),
    and we already validate values via `ProcessingStatus`/`ScanStatus`/
    `AlertLevel` enums before they reach the DB.
  * `id` is a `String(36)` carrying a UUID4 string, not a native UUID. The
    original schema chose this and we keep it: changing the column type
    would require a migration that rewrites every row, and the type change
    has no visible benefit at the API surface.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class StoredFile(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    # SHA-256 of the on-disk content. 64 hex chars; nullable for rows that
    # predate this column (production migrations don't backfill — a
    # background job can recompute lazily if ever needed).
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="uploaded"
    )
    scan_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scan_details: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # `metadata_json` rather than `metadata` because `metadata` is a reserved
    # attribute on SQLAlchemy's DeclarativeBase.
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    requires_attention: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("files.id"), nullable=False
    )
    level: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
