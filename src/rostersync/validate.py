"""Validation helpers for extracted roster rows."""

from __future__ import annotations

import datetime as dt

from rostersync.models import RosterDocument, RosterRow, ValidationIssue


def _parse_hhmm(value: str) -> dt.timedelta:
    hour, minute = map(int, value.split(":"))
    return dt.timedelta(hours=hour, minutes=minute)


def infer_cross_day(start_time: str | None, end_time: str | None) -> bool:
    """Return True when end time is earlier than start time (cross-day shift)."""
    if not start_time or not end_time:
        return False
    start = _parse_hhmm(start_time)
    end = _parse_hhmm(end_time)
    return end <= start


def compute_duration(start_time: str, end_time: str, *, cross_day: bool) -> dt.timedelta:
    """Compute shift duration from start/end times."""
    start = _parse_hhmm(start_time)
    end = _parse_hhmm(end_time)
    if cross_day or end <= start:
        end += dt.timedelta(days=1)
    return end - start


def validate_document(document: RosterDocument) -> list[ValidationIssue]:
    """Validate all rows: cross-day inference and hours checksum."""
    issues: list[ValidationIssue] = []

    for day in document.days:
        for row in day.rows:
            issues.extend(validate_row(day.date, row))

    return issues


def validate_row(day: dt.date, row: RosterRow) -> list[ValidationIssue]:
    """Validate one roster row."""
    issues: list[ValidationIssue] = []

    if not row.start_time or not row.end_time:
        return issues

    cross_day = infer_cross_day(row.start_time, row.end_time)
    computed = compute_duration(row.start_time, row.end_time, cross_day=cross_day)

    if row.hours:
        expected = _parse_hhmm(row.hours)
        if computed != expected:
            issues.append(
                ValidationIssue(
                    level="error",
                    day=day,
                    employee_id=row.employee_id,
                    nickname=row.nickname,
                    message=(
                        f"Hours mismatch for {row.nickname}: "
                        f"{row.start_time}-{row.end_time} => {format_timedelta(computed)}, "
                        f"expected {row.hours}"
                    ),
                )
            )

    return issues


def format_timedelta(delta: dt.timedelta) -> str:
    """Format timedelta as HH:mm."""
    total_minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"
