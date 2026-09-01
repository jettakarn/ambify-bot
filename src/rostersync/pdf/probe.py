"""Determine whether a PDF page has extractable text."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium


@dataclass(frozen=True)
class PdfProbeResult:
    """Summary of PDF characteristics for routing extraction."""

    page_count: int
    pages_with_text: int
    has_text_layer: bool


def probe_pdf(path: Path, *, min_chars_per_page: int = 20) -> PdfProbeResult:
    """Return whether the PDF has a usable text layer."""
    doc = pdfium.PdfDocument(str(path))
    page_count = len(doc)

    pages_with_text = 0
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = (page.extract_text() or "").strip()
            if len(text) >= min_chars_per_page:
                pages_with_text += 1

    return PdfProbeResult(
        page_count=page_count,
        pages_with_text=pages_with_text,
        has_text_layer=pages_with_text > 0,
    )
