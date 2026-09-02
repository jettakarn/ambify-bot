"""Column layout for Ambassador Theatres (國賓影城) daily roster pages.

Calibrated for native 2480px-wide rendered pages. Coordinates are ratios (0–1)
of page width so minor scale differences still work.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    x_min: float
    x_max: float


# Table body vertical range (skip company header; include section rows)
TABLE_Y_MIN = 0.15
TABLE_Y_MAX = 0.92
HEADER_Y_MAX = 0.12
NOTES_Y_MIN = 0.92

# Row clustering tolerance (~80px at 3507 height)
ROW_Y_TOLERANCE = 0.025

# Calibrated from 2480px Ambassador Bade branch rosters (OCR x-ratio)
COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("index", 0.00, 0.085),
    ColumnSpec("employee_id", 0.085, 0.115),
    ColumnSpec("nickname", 0.115, 0.205),
    ColumnSpec("start_time", 0.205, 0.265),
    ColumnSpec("end_time", 0.265, 0.325),
    ColumnSpec("hours", 0.325, 0.42),
)

EMPLOYEE_ID_MIN_LEN = 3
EMPLOYEE_ID_MAX_LEN = 8
