"""Tests for ICS generation."""

import datetime as dt

import icalendar

from twoshiftly.models import EmployeeSchedule, Shift
from twoshiftly.transform.ics import build_ics, esc, fold


def test_esc_special_characters():
    assert esc("a;b,c\\n") == "a\\;b\\,c\\\\n"


def test_build_ics_cross_day():
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
        ],
    )

    ics_bytes = build_ics(
        schedule,
        dtstamp=dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc),
    ).encode("utf-8")
    cal = icalendar.Calendar.from_ical(ics_bytes)
    events = list(cal.walk("VEVENT"))
    assert len(events) == 1
    assert "@2shiftly" in str(events[0].get("UID"))
    assert events[0].decoded("DTEND").hour == 1
