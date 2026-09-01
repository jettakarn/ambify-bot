"""Render PDF pages to PNG images using pypdfium2."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium


@dataclass(frozen=True)
class RenderedPage:
    """A rendered PDF page image."""

    page_index: int
    image_path: Path
    content_hash: str


def _page_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def render_pdf_pages(
    pdf_path: Path,
    output_dir: Path,
    *,
    target_width: int = 1700,
) -> list[RenderedPage]:
    """Render each PDF page to PNG and return metadata."""
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf_path))
    rendered: list[RenderedPage] = []

    for index in range(len(doc)):
        page = doc[index]
        scale = target_width / page.get_width()
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        image_path = output_dir / f"page{index + 1:02d}.png"
        pil_image.save(image_path, format="PNG")

        content_hash = _page_hash(image_path.read_bytes())
        rendered.append(
            RenderedPage(
                page_index=index,
                image_path=image_path,
                content_hash=content_hash,
            )
        )

    return rendered
