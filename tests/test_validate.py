"""Tests for validation helpers."""

import datetime as dt

from twoshiftly.models import RosterDocument, RosterRow
from twoshiftly.validate import (
    compute_duration,
    infer_cross_day,
    validate_document,
    validate_row,
)


def test_infer_cross_day_when_end_before_start():
    assert infer_cross_day("17:00", "01:00") is True
    assert infer_cross_day("17:00", "23:00") is False


def test_compute_duration_cross_day():
    duration = compute_duration("17:00", "01:00", cross_day=True)
    assert duration == dt.timedelta(hours=8)


def test_validate_row_hours_match():
    row = RosterRow(
        employee_id="1",
        nickname="Jetson",
        start_time="17:00",
        end_time="01:00",
        hours="08:00",
        section="售票部",
        day_type="平日",
    )
    issues = validate_row(dt.date(2026, 8, 21), row)
    assert issues == []


def test_validate_document_from_fixture(roster_document: RosterDocument):
    issues = validate_document(roster_document)
    assert issues == []
