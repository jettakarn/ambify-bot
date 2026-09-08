"""Filter roster document to one employee schedule."""

from __future__ import annotations

import datetime as dt

from twoshiftly.models import EmployeeSchedule, RosterDocument, RosterRow, Shift
from twoshiftly.validate import infer_cross_day


def _normalize_section(section: str) -> str:
    """Keep for OCR parsing; departments are not shown in schedule output."""
    if not section:
        return ""
    if any(k in section for k in ("訓練", "训练")):
        return "訓練員"
    if "售票" in section:
        return "售票部"
    if any(k in section for k in ("樓層", "楼层")):
        return "樓層"
    return section


def _match_row(
    row: RosterRow,
    *,
    employee: str | None,
    employee_id: str | None,
) -> bool:
    """Match a row by exact employee ID (preferred) or exact nickname."""
    if employee_id:
        return row.employee_id == employee_id.strip()
    if employee:
        return row.nickname.lower() == employee.strip().lower()
    return False


def find_employee(
    document: RosterDocument,
    *,
    employee: str | None = None,
    employee_id: str | None = None,
) -> tuple[str, str | None]:
    """Resolve employee nickname and id from document."""
    if not employee and not employee_id:
        raise ValueError("Provide --employee or --employee-id")

    for day in document.days:
        for row in day.rows:
            if _match_row(row, employee=employee, employee_id=employee_id):
                return row.nickname, row.employee_id

    names = sorted({row.nickname for day in document.days for row in day.rows})
    raise ValueError(
        f"Employee not found: {employee or employee_id}. "
        f"Available: {', '.join(names) if names else '(none)'}"
    )


def list_employees(document: RosterDocument) -> list[tuple[str, str]]:
    """Return unique (nickname, employee_id) pairs."""
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for day in document.days:
        for row in day.rows:
            key = (row.nickname, row.employee_id)
            if key not in seen:
                seen.add(key)
                result.append(key)
    return sorted(result, key=lambda item: item[0].lower())


def _row_to_shift(day: dt.date, row: RosterRow, weekday: str) -> Shift:
    day_type = row.day_type or "平日"
    cross_day = infer_cross_day(row.start_time, row.end_time)

    if row.start_time and row.end_time:
        shift_name = f"{day_type} {row.start_time}-{row.end_time}".strip()
    else:
        shift_name = "班"

    notes_parts = [weekday] if weekday else []
    if row.hours:
        notes_parts.append(f"時數 {row.hours}")
    if row.employee_id:
        notes_parts.append(f"員工代號 {row.employee_id}")

    return Shift(
        date=day,
        shift_name=shift_name,
        start_time=row.start_time,
        end_time=row.end_time,
        is_cross_day=cross_day,
        is_day_off=False,
        location=None,
        notes="；".join(notes_parts),
    )


def filter_employee_schedule(
    document: RosterDocument,
    *,
    employee: str | None = None,
    employee_id: str | None = None,
    infer_days_off: bool = True,
    off_note: str = "未出現於當日班表，推定休假",
) -> EmployeeSchedule:
    """Build an employee schedule from a full roster document."""
    name, resolved_id = find_employee(
        document,
        employee=employee,
        employee_id=employee_id,
    )

    if not document.days:
        raise ValueError("No days found in roster document")

    dates = sorted(day.date for day in document.days)
    year_month = dates[0].strftime("%Y-%m")
    shifts: list[Shift] = []

    for day in document.days:
        matched = [
            row
            for row in day.rows
            if _match_row(row, employee=name, employee_id=resolved_id)
        ]

        if matched:
            shifts.append(_row_to_shift(day.date, matched[0], day.weekday))
        elif infer_days_off:
            note = f"{day.weekday}；{off_note}" if day.weekday else off_note
            shifts.append(
                Shift(
                    date=day.date,
                    shift_name="OFF",
                    start_time=None,
                    end_time=None,
                    is_cross_day=False,
                    is_day_off=True,
                    location=None,
                    notes=note,
                )
            )

    return EmployeeSchedule(
        year_month=year_month,
        employee_name=name,
        employee_id=resolved_id,
        shifts=shifts,
    )
