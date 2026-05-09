"""Threat-scan rules.

This is one of the few places where the original behaviour is reproduced
verbatim — the test brief says 'do not break business logic', and the scan
rules are part of that contract. The encapsulation here is what changed:
a pure function with no I/O, easy to drive from a unit test with a table
of inputs.

The output is a `ScanResult` value object rather than mutating an ORM
instance directly, because:

  * It can be unit-tested without touching SQLAlchemy.
  * The caller (the Celery task) decides when and whether to apply the
    result, which is the right place for transactional concerns to live.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.domain.enums import ScanStatus

# Mirrors the original allow-list of suspicious extensions exactly. Kept
# here as a frozen set so an accidental mutation by another module is a
# loud TypeError rather than a subtle behaviour change.
_SUSPICIOUS_EXTENSIONS: frozenset[str] = frozenset(
    {".exe", ".bat", ".cmd", ".sh", ".js"}
)

# A PDF whose content-type doesn't admit it as a PDF is suspicious. The
# original code allowed `application/octet-stream` as a generic-binary
# escape hatch — keep that, otherwise direct downloads from some browsers
# (which omit the MIME) would always be flagged.
_PDF_ALLOWED_MIMES: frozenset[str] = frozenset(
    {"application/pdf", "application/octet-stream"}
)


@dataclass(frozen=True)
class ScanResult:
    status: ScanStatus
    details: str
    requires_attention: bool


class ScanService:
    def __init__(self, suspicious_size_bytes: int) -> None:
        self._max_safe_size = suspicious_size_bytes

    def scan(self, *, original_name: str, mime_type: str, size: int) -> ScanResult:
        reasons: list[str] = []
        extension = Path(original_name).suffix.lower()

        if extension in _SUSPICIOUS_EXTENSIONS:
            reasons.append(f"suspicious extension {extension}")

        if size > self._max_safe_size:
            reasons.append(
                # Phrased to match the original message format ("file is
                # larger than 10 MB"), so an alerting pipeline grepping for
                # this substring keeps working.
                f"file is larger than {self._max_safe_size // (1024 * 1024)} MB"
            )

        if extension == ".pdf" and mime_type not in _PDF_ALLOWED_MIMES:
            reasons.append("pdf extension does not match mime type")

        if reasons:
            return ScanResult(
                status=ScanStatus.SUSPICIOUS,
                details=", ".join(reasons),
                requires_attention=True,
            )
        return ScanResult(
            status=ScanStatus.CLEAN,
            details="no threats found",
            requires_attention=False,
        )
