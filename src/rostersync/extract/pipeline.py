"""Merge page extractions into a roster document."""

from __future__ import annotations

from pathlib import Path

from rostersync.extract.base import VisionExtractor
from rostersync.extract.cache import ExtractionCache
from rostersync.models import RosterDay, RosterDocument
from rostersync.pdf.render import RenderedPage, render_pdf_pages


def extract_scanned_roster(
    pdf_path: Path,
    extractor: VisionExtractor,
    *,
    cache_dir: Path | None = None,
    render_dir: Path | None = None,
    target_width: int = 1700,
) -> RosterDocument:
    """Extract a scanned roster by rendering pages and calling vision model."""
    if render_dir is None:
        render_dir = pdf_path.parent / ".rostersync" / "render"
    if cache_dir is None:
        cache_dir = pdf_path.parent / ".rostersync" / "cache"

    cache = ExtractionCache(cache_dir)
    rendered_pages = render_pdf_pages(pdf_path, render_dir, target_width=target_width)

    days: list[RosterDay] = []
    current_day: RosterDay | None = None

    for page in rendered_pages:
        extraction = cache.get(page.content_hash)
        if extraction is None:
            extraction = extractor.extract_page(page.image_path)
            cache.set(page.content_hash, extraction)

        if extraction.date is not None:
            if current_day is not None:
                days.append(current_day)
            current_day = RosterDay(
                date=extraction.date,
                weekday=extraction.weekday,
                rows=list(extraction.rows),
                page_notes=list(extraction.page_notes),
            )
        elif current_day is not None:
            current_day.rows.extend(extraction.rows)
            current_day.page_notes.extend(extraction.page_notes)
        elif extraction.rows:
            raise ValueError(
                f"Page {page.page_index + 1} has rows but no date header. "
                "Cannot merge continuation page without a preceding dated page."
            )

    if current_day is not None:
        days.append(current_day)

    return RosterDocument(source_file=str(pdf_path), days=days)
