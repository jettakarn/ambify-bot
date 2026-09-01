"""Extract roster tables from PDFs with a text layer."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pdfplumber

from rostersync.models import RosterDay, RosterDocument, RosterRow

DATE_HEADER_RE = re.compile(
    r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})"
)
WEEKDAY_RE = re.compile(r"(星期[一二三四五六日天]|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)")
SECTION_RE = re.compile(r"(平日|假日)(售票|樓層)")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")


def _parse_date_from_text(text: str) -> tuple[dt.date | None, str]:
    weekday = ""
    weekday_match = WEEKDAY_RE.search(text)
    if weekday_match:
        weekday = weekday_match.group(1)

    date_match = DATE_HEADER_RE.search(text)
    if not date_match:
        return None, weekday

    year, month, day = map(int, date_match.groups())
    return dt.date(year, month, day), weekday


def _normalize_time(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not TIME_RE.match(value):
        return None
    hour, minute = value.split(":")
    return f"{int(hour):02d}:{minute}"


def _parse_section_header(cell: str) -> tuple[str, str] | None:
    match = SECTION_RE.search(cell.replace("部", ""))
    if not match:
        return None
    day_type, section = match.groups()
    return day_type, section


def _row_from_cells(
    cells: list[str | None],
    *,
    day_type: str,
    section: str,
) -> RosterRow | None:
    values = [(cell or "").strip() for cell in cells]
    non_empty = [value for value in values if value]
    if len(non_empty) < 4:
        return None

    # Skip header / section rows.
    joined = "".join(values)
    if "員工代號" in joined or "暱稱" in joined or "總時數" in joined:
        return None
    if SECTION_RE.search(joined.replace("部", "")):
        return None

    # Typical columns: index, employee_id, nickname, start, end, hours, ...
    employee_id = values[1] if len(values) > 1 else ""
    nickname = values[2] if len(values) > 2 else ""
    start_time = _normalize_time(values[3] if len(values) > 3 else None)
    end_time = _normalize_time(values[4] if len(values) > 4 else None)
    hours = _normalize_time(values[5] if len(values) > 5 else None)

    if not employee_id or not nickname:
        return None
    if not start_time and not end_time:
        return None

    return RosterRow(
        employee_id=employee_id,
        nickname=nickname,
        start_time=start_time,
        end_time=end_time,
        hours=hours,
        section=section,
        day_type=day_type,
    )


def extract_text_roster(pdf_path: Path) -> RosterDocument:
    """Extract roster rows from a text-layer PDF using pdfplumber."""
    days: list[RosterDay] = []
    current_day: RosterDay | None = None
    current_day_type = ""
    current_section = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            page_date, weekday = _parse_date_from_text(page_text)

            if page_date is not None:
                if current_day is not None:
                    days.append(current_day)
                current_day = RosterDay(date=page_date, weekday=weekday)
                current_day_type = ""
                current_section = ""

            if current_day is None:
                continue

            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    cells = [str(cell).strip() if cell is not None else "" for cell in row]
                    joined = "".join(cells)
                    section_info = _parse_section_header(joined)
                    if section_info:
                        current_day_type, current_section = section_info
                        continue

                    parsed = _row_from_cells(
                        cells,
                        day_type=current_day_type,
                        section=current_section,
                    )
                    if parsed is not None:
                        current_day.rows.append(parsed)

    if current_day is not None:
        days.append(current_day)

    return RosterDocument(source_file=str(pdf_path), days=days)
