"""Generate RFC 5545 ICS calendar files from employee schedules."""

from __future__ import annotations

import datetime as dt
from typing import Iterable

from twoshiftly.models import EmployeeSchedule, Shift

VENUE = "國賓影城八德分公司"


def esc(text: str) -> str:
    """Escape a value per RFC 5545 TEXT rules."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def fold(line: str) -> list[str]:
    """Fold a content line to 75 octets on UTF-8 character boundaries."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return [line]

    out: list[str] = []
    buf = ""
    size = 0
    limit = 75
    for ch in line:
        n = len(ch.encode("utf-8"))
        if size + n > limit:
            out.append(buf)
            buf = ch
            size = n + 1
            limit = 75
        else:
            buf += ch
            size += n
    out.append(buf)
    return [out[0]] + [" " + part for part in out[1:]]


def _event_uid(shift: Shift, employee_name: str, employee_id: str | None) -> str:
    slug = (employee_id or employee_name).lower().replace(" ", "-")
    return f"{shift.date.strftime('%Y%m%d')}-{slug}@2shiftly"


def _calendar_name(schedule: EmployeeSchedule) -> str:
    if not schedule.shifts:
        return f"{schedule.employee_name} 班表"
    start = min(shift.date for shift in schedule.shifts)
    end = max(shift.date for shift in schedule.shifts)
    return f"{schedule.employee_name} 班表 {start:%Y/%m/%d}-{end:%m/%d}"


def build_ics(
    schedule: EmployeeSchedule,
    *,
    venue: str = VENUE,
    dtstamp: dt.datetime | None = None,
) -> str:
    """Build ICS calendar content from an employee schedule."""
    stamp = dtstamp or dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    stamp_str = stamp.strftime("%Y%m%dT%H%M%SZ")

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//2shiftly//twoshiftly//ZH-TW",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:" + esc(_calendar_name(schedule)),
        "X-WR-TIMEZONE:Asia/Taipei",
        "BEGIN:VTIMEZONE",
        "TZID:Asia/Taipei",
        "X-LIC-LOCATION:Asia/Taipei",
        "BEGIN:STANDARD",
        "DTSTART:19700101T000000",
        "TZOFFSETFROM:+0800",
        "TZOFFSETTO:+0800",
        "TZNAME:CST",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]

    for shift in schedule.shifts:
        lines.extend(
            _event_lines(
                shift,
                employee_name=schedule.employee_name,
                employee_id=schedule.employee_id,
                venue=venue,
                dtstamp=stamp_str,
            )
        )

    lines.append("END:VCALENDAR")

    folded: list[str] = []
    for line in lines:
        folded.extend(fold(line))
    return "\r\n".join(folded) + "\r\n"


def _event_lines(
    shift: Shift,
    *,
    employee_name: str,
    employee_id: str | None,
    venue: str,
    dtstamp: str,
) -> Iterable[str]:
    uid = _event_uid(shift, employee_name, employee_id)
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
    ]

    if shift.is_day_off:
        next_day = shift.date + dt.timedelta(days=1)
        lines.extend(
            [
                "DTSTART;VALUE=DATE:" + shift.date.strftime("%Y%m%d"),
                "DTEND;VALUE=DATE:" + next_day.strftime("%Y%m%d"),
                "SUMMARY:" + esc("休假 OFF"),
                "TRANSP:TRANSPARENT",
            ]
        )
    else:
        assert shift.start_time and shift.end_time
        start = dt.datetime.strptime(
            f"{shift.date.isoformat()} {shift.start_time}",
            "%Y-%m-%d %H:%M",
        )
        end = dt.datetime.strptime(
            f"{shift.date.isoformat()} {shift.end_time}",
            "%Y-%m-%d %H:%M",
        )
        if shift.is_cross_day:
            end += dt.timedelta(days=1)

        summary = f"{venue} {shift.location or ''} {shift.start_time}-{shift.end_time}".strip()
        lines.extend(
            [
                "DTSTART;TZID=Asia/Taipei:" + start.strftime("%Y%m%dT%H%M%S"),
                "DTEND;TZID=Asia/Taipei:" + end.strftime("%Y%m%dT%H%M%S"),
                "SUMMARY:" + esc(summary),
                "LOCATION:" + esc(venue),
                "TRANSP:OPAQUE",
            ]
        )

    description = shift.shift_name
    if shift.notes:
        description = f"{shift.shift_name}\n{shift.notes}"
    lines.append("DESCRIPTION:" + esc(description))
    lines.append("END:VEVENT")
    return lines
