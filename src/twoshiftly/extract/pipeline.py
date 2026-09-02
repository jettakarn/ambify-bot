"""Merge OCR page extractions into a roster document."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from twoshiftly.extract.ambassador.page_parser import parse_ambassador_page
from twoshiftly.extract.cache import ExtractionCache
from twoshiftly.extract.ocr import run_ocr
from twoshiftly.models import RosterDay, RosterDocument
from twoshiftly.pdf.render import DEFAULT_RENDER_WIDTH, render_pdf_pages


def extract_scanned_roster(
    pdf_path: Path,
    *,
    cache_dir: Path | None = None,
    render_dir: Path | None = None,
    target_width: int = DEFAULT_RENDER_WIDTH,
    on_page: Callable[[int, int], None] | None = None,
) -> RosterDocument:
    """Extract a scanned roster via local OCR and Ambassador layout rules."""
    if render_dir is None:
        render_dir = pdf_path.parent / ".twoshiftly" / "render"
    if cache_dir is None:
        cache_dir = pdf_path.parent / ".twoshiftly" / "cache"

    cache = ExtractionCache(cache_dir)
    rendered_pages = render_pdf_pages(pdf_path, render_dir, target_width=target_width)

    days: list[RosterDay] = []
    current_day: RosterDay | None = None
    total_pages = len(rendered_pages)

    for index, page in enumerate(rendered_pages):
        if on_page is not None:
            on_page(index + 1, total_pages)

        extraction = cache.get(page.content_hash)
        if extraction is None:
            boxes = run_ocr(page.image_path)
            extraction = parse_ambassador_page(
                boxes,
                page_width=page.width,
                page_height=page.height,
            )
            cache.set(page.content_hash, extraction)

        if extraction.date is not None:
            if current_day is not None and current_day.date == extraction.date:
                current_day.rows.extend(extraction.rows)
                current_day.page_notes.extend(extraction.page_notes)
            else:
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
