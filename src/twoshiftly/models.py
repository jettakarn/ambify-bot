"""Pydantic data models for roster extraction and calendar export."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RosterRow(BaseModel):
    """One employee shift row from a daily roster page."""

    employee_id: str
    nickname: str
    start_time: str | None = None
    end_time: str | None = None
    hours: str | None = None
    section: str = ""
    day_type: str = ""

    @field_validator("employee_id", mode="before")
    @classmethod
    def normalize_employee_id(cls, value: object) -> str:
        return str(value).strip()

    @field_validator("nickname", "section", "day_type", mode="before")
    @classmethod
    def strip_strings(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()


class RosterDay(BaseModel):
    """All shift rows for one calendar date."""

    date: dt.date
    weekday: str = ""
    rows: list[RosterRow] = Field(default_factory=list)
    page_notes: list[str] = Field(default_factory=list)


class RosterDocument(BaseModel):
    """Full extracted roster spanning multiple days."""

    source_file: str
    days: list[RosterDay] = Field(default_factory=list)

    @property
    def date_range(self) -> tuple[dt.date, dt.date] | None:
        if not self.days:
            return None
        dates = sorted(day.date for day in self.days)
        return dates[0], dates[-1]


class Shift(BaseModel):
    """Output-layer shift record for JSON / ICS export."""

    date: dt.date
    shift_name: str
    start_time: str | None = None
    end_time: str | None = None
    is_cross_day: bool = False
    is_day_off: bool = False
    location: str | None = None
    notes: str = ""


class EmployeeSchedule(BaseModel):
    """Filtered schedule for one employee."""

    year_month: str
    employee_name: str
    employee_id: str | None = None
    timezone: Literal["Asia/Taipei"] = "Asia/Taipei"
    shifts: list[Shift] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    """A validation warning or error from hours/cross-day checks."""

    level: Literal["warning", "error"]
    day: dt.date
    employee_id: str
    nickname: str
    message: str


class PageExtraction(BaseModel):
    """Parsed content from a single roster page."""

    date: dt.date | None = None
    weekday: str = ""
    rows: list[RosterRow] = Field(default_factory=list)
    page_notes: list[str] = Field(default_factory=list)
