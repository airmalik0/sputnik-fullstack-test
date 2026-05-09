"""Metadata extraction tests.

These exercise the two interesting branches: text/* line+char counting
with the byte cap honoured, and PDF parsing via pypdf. We intentionally
do not mock pypdf — the integration with a real PdfReader is what we
care about validating.
"""

from datetime import datetime
from pathlib import Path

from pypdf import PdfWriter

from src.domain.models import StoredFile
from src.services.metadata_extractor import MetadataExtractor


def _file(**overrides) -> StoredFile:
    base = StoredFile(
        id="00000000-0000-0000-0000-000000000000",
        title="t",
        original_name="file.bin",
        stored_name="00000000-0000-0000-0000-000000000000.bin",
        mime_type="application/octet-stream",
        size=0,
        sha256=None,
        processing_status="uploaded",
        scan_status=None,
        scan_details=None,
        metadata_json=None,
        requires_attention=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_text_metadata_counts_lines_and_chars(tmp_path: Path):
    extractor = MetadataExtractor(text_byte_limit=1024)
    blob = tmp_path / "x.txt"
    blob.write_text("alpha\nbeta\ngamma\n")
    file = _file(original_name="x.txt", mime_type="text/plain", size=blob.stat().st_size)

    md = extractor.extract(file, blob)

    assert md["mime_type"] == "text/plain"
    assert md["extension"] == ".txt"
    assert md["size_bytes"] == file.size
    assert md["line_count"] == 3
    # str.splitlines on "a\nb\nc\n" returns 3 entries; char_count is the
    # decoded character length, including newlines.
    assert md["char_count"] == len("alpha\nbeta\ngamma\n")


def test_text_metadata_honours_byte_cap(tmp_path: Path):
    # Cap is much smaller than the file. The extractor must not OOM and
    # must report counts derived from the truncated read.
    extractor = MetadataExtractor(text_byte_limit=64)
    blob = tmp_path / "big.txt"
    blob.write_text(("line\n" * 10_000))  # ~50 KB, well past the cap
    file = _file(original_name="big.txt", mime_type="text/plain", size=blob.stat().st_size)

    md = extractor.extract(file, blob)

    # We read at most 64 bytes; "line\n" is 5 bytes, so we got 12 full
    # lines and at most 13 with a partial. Bound rather than exact match
    # because the str.splitlines edge case for trailing partial lines
    # makes an exact assertion brittle.
    assert md["char_count"] <= 64
    assert md["line_count"] <= 13


def test_pdf_metadata_counts_pages(tmp_path: Path):
    extractor = MetadataExtractor(text_byte_limit=1024)
    writer = PdfWriter()
    for _ in range(4):
        writer.add_blank_page(width=72, height=72)
    blob = tmp_path / "doc.pdf"
    with blob.open("wb") as fh:
        writer.write(fh)
    file = _file(
        original_name="doc.pdf", mime_type="application/pdf", size=blob.stat().st_size
    )

    md = extractor.extract(file, blob)

    assert md["approx_page_count"] == 4
    assert md["mime_type"] == "application/pdf"


def test_pdf_metadata_handles_malformed_file(tmp_path: Path):
    extractor = MetadataExtractor(text_byte_limit=1024)
    blob = tmp_path / "broken.pdf"
    blob.write_bytes(b"this is not a pdf")
    file = _file(
        original_name="broken.pdf", mime_type="application/pdf", size=blob.stat().st_size
    )

    md = extractor.extract(file, blob)

    # Malformed input must not raise out of the pipeline; a conservative
    # fallback page count keeps the alert path running.
    assert md["approx_page_count"] == 1
