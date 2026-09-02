"""Tests for OCR pipeline progress callback."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import datetime as dt

from twoshiftly.extract.pipeline import extract_scanned_roster
from twoshiftly.models import PageExtraction, RosterRow
from twoshiftly.pdf.render import RenderedPage


def test_extract_scanned_roster_calls_on_page(tmp_path: Path):
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF")

    pages = [
        RenderedPage(
            page_index=0,
            image_path=tmp_path / "p1.png",
            content_hash="aaa",
            width=2480,
            height=3507,
        ),
    ]
    extraction = PageExtraction(
        date=dt.date(2026, 8, 21),
        weekday="星期五",
        rows=[
            RosterRow(
                employee_id="1324401",
                nickname="Jetson",
                start_time="17:00",
                end_time="01:00",
                hours="08:00",
                section="售票部",
                day_type="平日",
            )
        ],
    )

    progress: list[tuple[int, int]] = []

    with patch("twoshiftly.extract.pipeline.render_pdf_pages", return_value=pages):
        with patch("twoshiftly.extract.pipeline.run_ocr", return_value=[]):
            with patch(
                "twoshiftly.extract.pipeline.parse_ambassador_page",
                return_value=extraction,
            ):
                with patch("twoshiftly.extract.pipeline.ExtractionCache") as cache_cls:
                    cache = cache_cls.return_value
                    cache.get.return_value = None
                    doc = extract_scanned_roster(
                        pdf,
                        cache_dir=tmp_path / "cache",
                        render_dir=tmp_path / "render",
                        on_page=lambda c, t: progress.append((c, t)),
                    )

    assert progress == [(1, 1)]
    assert len(doc.days) == 1
    assert doc.days[0].rows[0].nickname == "Jetson"


def test_extract_scanned_roster_merges_same_date_pages(tmp_path: Path):
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF")

    pages = [
        RenderedPage(
            page_index=0,
            image_path=tmp_path / "p1.png",
            content_hash="aaa",
            width=2480,
            height=3507,
        ),
        RenderedPage(
            page_index=1,
            image_path=tmp_path / "p2.png",
            content_hash="bbb",
            width=2480,
            height=3507,
        ),
    ]
    ticket_row = RosterRow(
        employee_id="1324401",
        nickname="Jetson",
        start_time="17:00",
        end_time="01:00",
        hours="08:00",
        section="售票部",
        day_type="平日",
    )
    floor_row = RosterRow(
        employee_id="1329901",
        nickname="Staff",
        start_time="09:00",
        end_time="18:00",
        hours="09:00",
        section="樓層",
        day_type="平日",
    )
    extractions = [
        PageExtraction(date=dt.date(2026, 8, 21), weekday="星期五", rows=[ticket_row]),
        PageExtraction(date=dt.date(2026, 8, 21), weekday="星期五", rows=[floor_row]),
    ]

    with patch("twoshiftly.extract.pipeline.render_pdf_pages", return_value=pages):
        with patch("twoshiftly.extract.pipeline.run_ocr", return_value=[]):
            with patch(
                "twoshiftly.extract.pipeline.parse_ambassador_page",
                side_effect=extractions,
            ):
                with patch("twoshiftly.extract.pipeline.ExtractionCache") as cache_cls:
                    cache = cache_cls.return_value
                    cache.get.return_value = None
                    doc = extract_scanned_roster(
                        pdf,
                        cache_dir=tmp_path / "cache",
                        render_dir=tmp_path / "render",
                    )

    assert len(doc.days) == 1
    assert len(doc.days[0].rows) == 2
    assert doc.days[0].rows[0].nickname == "Jetson"
    assert doc.days[0].rows[1].nickname == "Staff"
