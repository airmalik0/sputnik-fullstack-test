"""Pure metadata extraction.

Sits in the services package because it is reusable business logic, but
unlike FileService it has no persistence concerns — it takes a path on
disk and returns a dict. That shape makes it easy to test against
fixture files and easy to call from the Celery task.

The output dict shape mirrors the original implementation's contract
exactly: extension, size_bytes, mime_type for every file, plus
line_count/char_count for text/* and approx_page_count for PDFs.

Two perf-relevant changes versus the original:

  * PDFs are parsed with `pypdf` (which streams) instead of slurping the
    whole file and counting `/Type /Page` byte sequences. That heuristic
    was both expensive (read the entire file into memory) and inaccurate
    on non-canonical PDFs that use compressed object streams or
    differently-formatted Type entries.
  * Text files cap their read at a configurable byte limit. The original
    code called `read_text()` unconditionally — uploading a 5 GB log file
    as text/plain would have OOM'd the worker. The cap is a knob in
    Settings rather than a magic number here.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.domain.models import StoredFile

logger = logging.getLogger(__name__)


class MetadataExtractor:
    def __init__(self, text_byte_limit: int) -> None:
        self._text_byte_limit = text_byte_limit

    def extract(self, file: StoredFile, on_disk: Path) -> dict:
        metadata: dict = {
            "extension": Path(file.original_name).suffix.lower(),
            "size_bytes": file.size,
            "mime_type": file.mime_type,
        }
        if file.mime_type.startswith("text/"):
            metadata.update(self._text_metadata(on_disk))
        elif file.mime_type == "application/pdf":
            metadata.update(self._pdf_metadata(on_disk))
        return metadata

    def _text_metadata(self, on_disk: Path) -> dict:
        # Read up to the configured limit in binary, then decode. Reading
        # binary first is cheaper than the "read_text" path because it
        # avoids decoding bytes we are about to throw away.
        with on_disk.open("rb") as fh:
            raw = fh.read(self._text_byte_limit)
        content = raw.decode("utf-8", errors="ignore")
        # `splitlines` is slightly more accurate than `count("\n")` —
        # handles trailing-newline edge cases and CRLF line endings the
        # same way the original implementation did via str.splitlines().
        return {
            "line_count": len(content.splitlines()),
            "char_count": len(content),
        }

    def _pdf_metadata(self, on_disk: Path) -> dict:
        # PdfReader opens the file lazily and reads only the trailer +
        # cross-reference table to enumerate pages. For a 100 MB PDF
        # this is megabytes of I/O instead of all 100.
        try:
            reader = PdfReader(str(on_disk))
            return {"approx_page_count": max(len(reader.pages), 1)}
        except PdfReadError as exc:
            # Malformed PDF — fall back to a conservative answer rather
            # than failing the whole pipeline. Logged so the on-call has
            # something to investigate if it becomes a pattern.
            logger.warning(
                "PDF metadata extraction failed for %s: %s",
                on_disk.name,
                exc,
            )
            return {"approx_page_count": 1}
