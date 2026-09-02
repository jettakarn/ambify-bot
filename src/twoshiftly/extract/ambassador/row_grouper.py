"""Group OCR boxes into table rows and assign column values."""

from __future__ import annotations

from dataclasses import dataclass

from twoshiftly.extract.ambassador.layout import COLUMNS, ColumnSpec
from twoshiftly.extract.ocr import OcrBox


@dataclass
class TableRow:
    y: float
    cells: dict[str, str]


def _assign_column(x: float, page_width: float, columns: tuple[ColumnSpec, ...]) -> str | None:
    ratio = x / page_width
    for column in columns:
        if column.x_min <= ratio < column.x_max:
            return column.name
    return None


def group_boxes_into_rows(
    boxes: list[OcrBox],
    *,
    page_width: float,
    page_height: float,
    y_min: float,
    y_max: float,
    y_tolerance_ratio: float,
) -> list[TableRow]:
    """Cluster OCR boxes in the table region into rows."""
    tolerance = y_tolerance_ratio * page_height
    table_boxes = [
        box
        for box in boxes
        if y_min * page_height <= box.y <= y_max * page_height
    ]
    table_boxes.sort(key=lambda b: (b.y, b.x))

    rows: list[TableRow] = []
    current: TableRow | None = None

    for box in table_boxes:
        column = _assign_column(box.x, page_width, COLUMNS)
        if column is None:
            continue

        if current is None or abs(box.y - current.y) > tolerance:
            current = TableRow(y=box.y, cells={})
            rows.append(current)
        else:
            current.y = (current.y + box.y) / 2

        existing = current.cells.get(column, "")
        current.cells[column] = f"{existing} {box.text}".strip() if existing else box.text

    return rows
