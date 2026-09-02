"""Tests for employee filtering."""

import datetime as dt

import pytest

from twoshiftly.models import RosterDocument
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
