"""Smoke tests for the local web UI API."""

from __future__ import annotations

import datetime as dt
from unittest.mock import patch

from fastapi.testclient import TestClient

from twoshiftly.models import RosterDay, RosterDocument, RosterRow, ValidationIssue
from twoshiftly.web.server import app
from twoshiftly.web.jobs import store


def _sample_document() -> RosterDocument:
    return RosterDocument(
        source_file="roster.pdf",
        days=[
            RosterDay(
                date=dt.date(2026, 8, 21),
                weekday="星期五",
                rows=[
                    RosterRow(
                        employee_id="1324401",
                        nickname="Jetson",
                        start_time="17:00",
                        end_time="01:00",
                        hours="08:00",
                        section="售票部",
                        day_type="平日",
                    )
                ],
            )
        ],
    )


def test_upload_list_ics_flow(tmp_path):
    store.clear_all()
    document = _sample_document()
    issues = [
        ValidationIssue(
            level="warning",
            day=dt.date(2026, 8, 21),
            employee_id="x",
            nickname="x",
            message="sample warning",
        )
    ]

    def fake_load(pdf_path, **kwargs):
        on_page = kwargs.get("on_page")
        if on_page:
            on_page(1, 1)
        return document, issues

    with patch("twoshiftly.web.server.load_roster_document", side_effect=fake_load):
        with TestClient(app) as client:
            response = client.post(
                "/api/upload",
                files={"file": ("roster.pdf", b"%PDF-1.4 sample", "application/pdf")},
            )
            assert response.status_code == 200
            job_id = response.json()["job_id"]

            status = client.get(f"/api/jobs/{job_id}")
            assert status.status_code == 200
            payload = status.json()
            assert payload["status"] == "ready"
            assert payload["employees"] == [
                {"nickname": "Jetson", "employee_id": "1324401"}
            ]
            assert payload["date_start"] == "2026-08-21"

            ics = client.post(
                f"/api/jobs/{job_id}/ics",
                json={"employee": "Jetson", "employee_id": "1324401"},
            )
            assert ics.status_code == 200
            body = ics.text
            assert "BEGIN:VCALENDAR" in body
            assert "@2shiftly" in body

            schedule = client.post(
                f"/api/jobs/{job_id}/schedule",
                json={"employee": "Jetson", "employee_id": "1324401"},
            )
            assert schedule.status_code == 200
            payload_schedule = schedule.json()
            assert payload_schedule["employee_name"] == "Jetson"
            assert payload_schedule["employee_id"] == "1324401"
            assert len(payload_schedule["shifts"]) >= 1
            assert payload_schedule["shifts"][0]["start_time"] == "17:00"
            assert payload_schedule["shifts"][0]["end_time"] == "01:00"


def test_schedule_not_found_employee():
    store.clear_all()
    document = _sample_document()

    def fake_load(pdf_path, **kwargs):
        return document, []

    with patch("twoshiftly.web.server.load_roster_document", side_effect=fake_load):
        with TestClient(app) as client:
            job_id = client.post(
                "/api/upload",
                files={"file": ("roster.pdf", b"%PDF-1.4 sample", "application/pdf")},
            ).json()["job_id"]
            response = client.post(
                f"/api/jobs/{job_id}/schedule",
                json={"employee": "Nobody"},
            )
    assert response.status_code == 404


def test_upload_rejects_non_pdf():
    store.clear_all()
    with TestClient(app) as client:
        response = client.post(
            "/api/upload",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
    assert response.status_code == 400


def test_index_page_serves_search_ui():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "2shiftly" in response.text
    assert "search-input" in response.text
    assert 'placeholder="輸入員工或員編"' in response.text
    assert "下載行事曆" in response.text
    assert "複製班表文字" in response.text
