"""Status enumerations.

These replace bare string literals scattered across the original code. Using
`str, Enum` is deliberate:

  * Values stay wire-compatible with the existing API contract — Pydantic
    serialises members to their string value, so the JSON schema and the
    response payloads are byte-identical to what the original implementation
    produced.
  * The DB columns remain VARCHAR (see `domain/models.py`). We did not
    migrate to a Postgres ENUM type because that would require an Alembic
    migration with locking implications and brings no observable benefit
    here — the validation belongs in the application layer.
  * Misspellings ("uplodaed", "Suspicious") become impossible at the type
    level instead of slipping through to production.
"""

from enum import Enum


class ProcessingStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ScanStatus(str, Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    FAILED = "failed"


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
