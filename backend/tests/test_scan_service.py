"""Scan rules driven by a parameterised truth table.

Each row maps an input (filename, mime, size) to the expected scan
verdict. This is the right shape for these tests: the service is a pure
function over its inputs, so a table is the most legible
specification.
"""

import pytest

from src.domain.enums import ScanStatus
from src.services.scan_service import ScanService

SUSPICIOUS_SIZE = 10 * 1024 * 1024
scanner = ScanService(suspicious_size_bytes=SUSPICIOUS_SIZE)


@pytest.mark.parametrize(
    "name,mime,size,expected_status,detail_substring",
    [
        # Clean cases — common shapes that must not be flagged.
        ("doc.pdf", "application/pdf", 1024, ScanStatus.CLEAN, "no threats"),
        # PDF with octet-stream is the original allow-list escape hatch.
        ("doc.pdf", "application/octet-stream", 1024, ScanStatus.CLEAN, "no threats"),
        ("memo.txt", "text/plain", 100, ScanStatus.CLEAN, "no threats"),
        ("photo.jpg", "image/jpeg", 5_000_000, ScanStatus.CLEAN, "no threats"),

        # Extension blocklist hits.
        ("payload.exe", "application/octet-stream", 100, ScanStatus.SUSPICIOUS, "suspicious extension .exe"),
        ("run.bat", "text/plain", 100, ScanStatus.SUSPICIOUS, "suspicious extension .bat"),
        ("run.cmd", "text/plain", 100, ScanStatus.SUSPICIOUS, "suspicious extension .cmd"),
        ("run.sh", "text/plain", 100, ScanStatus.SUSPICIOUS, "suspicious extension .sh"),
        ("script.JS", "application/javascript", 100, ScanStatus.SUSPICIOUS, "suspicious extension .js"),  # case-insensitive

        # Size threshold (strictly greater than, mirroring the original).
        ("big.bin", "application/octet-stream", SUSPICIOUS_SIZE + 1, ScanStatus.SUSPICIOUS, "larger than 10 MB"),
        ("edge.bin", "application/octet-stream", SUSPICIOUS_SIZE, ScanStatus.CLEAN, "no threats"),

        # PDF/MIME mismatch — only PDF extension triggers this rule.
        ("fake.pdf", "image/png", 100, ScanStatus.SUSPICIOUS, "pdf extension does not match"),
        # Non-PDF file with weird MIME is fine — rule is scoped to .pdf.
        ("data.bin", "image/png", 100, ScanStatus.CLEAN, "no threats"),

        # Stacking: suspicious extension AND oversize accumulates reasons.
        ("big.exe", "application/octet-stream", SUSPICIOUS_SIZE + 1, ScanStatus.SUSPICIOUS, "suspicious extension .exe"),
    ],
)
def test_scan_rules(name, mime, size, expected_status, detail_substring):
    result = scanner.scan(original_name=name, mime_type=mime, size=size)
    assert result.status == expected_status
    assert detail_substring in result.details
    # requires_attention is the boolean projection of "is this not clean".
    assert result.requires_attention == (expected_status is ScanStatus.SUSPICIOUS)


def test_stacked_reasons_are_joined():
    result = scanner.scan(
        original_name="big.exe",
        mime_type="application/octet-stream",
        size=SUSPICIOUS_SIZE + 1,
    )
    # Both rules fired; the joined details must mention both reasons so
    # the alert message is informative.
    assert "suspicious extension .exe" in result.details
    assert "larger than 10 MB" in result.details
