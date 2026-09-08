"""Tests for employee filtering."""

import datetime as dt

import pytest

from twoshiftly.models import RosterDay, RosterDocument, RosterRow
from twoshiftly.transform.filter import filter_employee_schedule, find_employee, list_employees


def test_list_employees(roster_document: RosterDocument):
    employees = list_employees(roster_document)
    names = {name for name, _ in employees}
    assert "Jetson" in names


def test_find_employee_by_nickname(roster_document: RosterDocument):
    name, emp_id = find_employee(roster_document, employee="Jetson")
    assert name == "Jetson"
    assert emp_id == "1324401"


def test_find_employee_not_found(roster_document: RosterDocument):
    with pytest.raises(ValueError, match="Employee not found"):
        find_employee(roster_document, employee="Nobody")


def test_filter_with_inferred_days_off(roster_document: RosterDocument):
    schedule = filter_employee_schedule(
        roster_document,
        employee="Jetson",
        infer_days_off=True,
    )
    assert len(schedule.shifts) == 5
    off_days = [s for s in schedule.shifts if s.is_day_off]
    assert len(off_days) == 1


def test_similar_nickname_does_not_steal_match():
    doc = RosterDocument(
        source_file="t.pdf",
        days=[
            RosterDay(
                date=dt.date(2026, 8, 21),
                weekday="星期五",
                rows=[
                    RosterRow(
                        employee_id="1001",
                        nickname="Evan",
                        start_time="09:00",
                        end_time="18:00",
                        hours="09:00",
                        section="樓層",
                        day_type="平日",
                    ),
                    RosterRow(
                        employee_id="1002",
                        nickname="Eva",
                        start_time="17:00",
                        end_time="01:00",
                        hours="08:00",
                        section="售票部",
                        day_type="平日",
                    ),
                ],
            )
        ],
    )
    by_id = filter_employee_schedule(doc, employee="Eva", employee_id="1002")
    assert by_id.employee_name == "Eva"
    assert by_id.employee_id == "1002"
    assert by_id.shifts[0].start_time == "17:00"
    assert by_id.shifts[0].location is None

    by_name = filter_employee_schedule(doc, employee="Eva")
    assert by_name.employee_name == "Eva"
    assert by_name.employee_id == "1002"

    with pytest.raises(ValueError, match="Employee not found"):
        find_employee(doc, employee="ev")
