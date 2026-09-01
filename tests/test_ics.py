"""Tests for ICS generation."""

import datetime as dt

import icalendar

from rostersync.models import EmployeeSchedule, Shift
from rostersync.transform.ics import build_ics, esc, fold


def test_esc_special_characters():
    assert esc("a;b,c\\n") == "a\\;b\\,c\\\\n"


def test_fold_long_utf8_line():
    line = "SUMMARY:" + "國" * 40
    folded = fold(line)
    assert len(folded) > 1
    assert folded[1].startswith(" ")


def test_build_ics_cross_day_and_day_off():
    schedule = EmployeeSchedule(
        year_month="2026-08",
        employee_name="Jetson",
        employee_id="1324401",
        shifts=[
            Shift(
                date=dt.date(2026, 8, 21),
                shift_name="平日售票部 17:00-01:00",
                start_time="17:00",
                end_time="01:00",
                is_cross_day=True,
                is_day_off=False,
                location="售票部",
                notes="星期五；時數 08:00",
            ),
            Shift(
                date=dt.date(2026, 8, 23),
                shift_name="OFF",
                is_day_off=True,
                notes="星期日；推定休假",
            ),
        ],
    )

    ics_bytes = build_ics(
        schedule,
        dtstamp=dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc),
    ).encode("utf-8")
    cal = icalendar.Calendar.from_ical(ics_bytes)

    events = list(cal.walk("VEVENT"))
    assert len(events) == 2

    work = events[0]
    assert work.decoded("DTSTART").hour == 17
    assert work.decoded("DTEND").day == 22
    assert work.decoded("DTEND").hour == 1

    off = events[1]
    assert off.decoded("SUMMARY") == "休假 OFF"
    assert off.get("TRANSP") == "TRANSPARENT"
