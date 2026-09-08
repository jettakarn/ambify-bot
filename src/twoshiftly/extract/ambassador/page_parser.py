"""Parse one Ambassador Theatres roster page from OCR boxes."""

from __future__ import annotations

from twoshiftly.extract.ambassador import layout
from twoshiftly.extract.ambassador.row_grouper import group_boxes_into_rows
from twoshiftly.extract.ambassador.section_detector import (
    clean_row_cells,
    is_header_row,
    is_section_row,
    looks_like_employee_id,
    normalize_time,
    parse_page_date,
    parse_section,
)
from twoshiftly.extract.ocr import OcrBox
from twoshiftly.models import PageExtraction, RosterRow


def _section_marks_from_boxes(
    boxes: list[OcrBox],
    *,
    page_width: float,
    page_height: float,
) -> list[tuple[float, str, str]]:
    """Collect section headers from raw OCR boxes (any column / left margin)."""
    marks: list[tuple[float, str, str]] = []
    y_min = layout.TABLE_Y_MIN * page_height
    y_max = layout.TABLE_Y_MAX * page_height
    for box in boxes:
        if not (y_min <= box.y <= y_max):
            continue
        # Section titles sit on the left; ignore far-right noise.
        if box.x > 0.45 * page_width:
            continue
        info = parse_section(box.text)
        if info is None:
            continue
        day_type, section = info
        marks.append((box.y, day_type, section))
    marks.sort(key=lambda item: item[0])
    return marks


def parse_ambassador_page(
    boxes: list[OcrBox],
    *,
    page_width: int,
    page_height: int,
) -> PageExtraction:
    """Convert OCR boxes from one page into structured roster data."""
    page_date, weekday = parse_page_date(
        boxes,
        header_y_max=layout.HEADER_Y_MAX,
        page_height=page_height,
    )

    table_rows = group_boxes_into_rows(
        boxes,
        page_width=page_width,
        page_height=page_height,
        y_min=layout.TABLE_Y_MIN,
        y_max=layout.TABLE_Y_MAX,
        y_tolerance_ratio=layout.ROW_Y_TOLERANCE,
    )

    section_marks = _section_marks_from_boxes(
        boxes,
        page_width=page_width,
        page_height=page_height,
    )
    mark_idx = 0
    y_slop = layout.ROW_Y_TOLERANCE * page_height

    rows: list[RosterRow] = []
    current_day_type = ""
    current_section = ""

    for table_row in table_rows:
        while mark_idx < len(section_marks) and section_marks[mark_idx][0] <= table_row.y + y_slop:
            day_type, section = section_marks[mark_idx][1], section_marks[mark_idx][2]
            if day_type:
                current_day_type = day_type
            current_section = section
            mark_idx += 1

        cell_texts = list(table_row.cells.values())
        joined = "".join(cell_texts)

        section_info = parse_section(joined)
        if section_info:
            day_type, section = section_info
            if day_type:
                current_day_type = day_type
            current_section = section
            continue

        if is_header_row(cell_texts):
            continue

        if is_section_row(cell_texts) and not looks_like_employee_id(
            table_row.cells.get("employee_id", "")
        ):
            continue

        cells = clean_row_cells(table_row.cells)
        employee_id = cells.get("employee_id", "").strip()
        nickname = cells.get("nickname", "").strip()
        if not looks_like_employee_id(employee_id) or not nickname:
            continue

        start_time = normalize_time(cells.get("start_time"))
        end_time = normalize_time(cells.get("end_time"))
        hours = normalize_time(cells.get("hours"))
        if not start_time and not end_time:
            continue

        rows.append(
            RosterRow(
                employee_id=employee_id,
                nickname=nickname,
                start_time=start_time,
                end_time=end_time,
                hours=hours,
                section=current_section,
                day_type=current_day_type,
            )
        )

    notes: list[str] = []
    note_limit = layout.NOTES_Y_MIN * page_height
    for box in boxes:
        if box.y >= note_limit and len(box.text) > 4:
            if "頁次" not in box.text and "國賓" not in box.text:
                notes.append(box.text)

    return PageExtraction(
        date=page_date,
        weekday=weekday,
        rows=rows,
        page_notes=notes,
    )
