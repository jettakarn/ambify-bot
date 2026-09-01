"""Prompt and JSON schema for Ambassador Theatres roster pages."""

from __future__ import annotations

PAGE_EXTRACTION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "date": {
            "type": ["string", "null"],
            "description": "Shift date in YYYY-MM-DD from page header, or null if continuation page",
        },
        "weekday": {
            "type": "string",
            "description": "Weekday label from header, e.g. 星期五",
        },
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "nickname": {"type": "string"},
                    "start_time": {"type": ["string", "null"]},
                    "end_time": {"type": ["string", "null"]},
                    "hours": {"type": ["string", "null"]},
                    "section": {
                        "type": "string",
                        "description": "售票部 or 樓層",
                    },
                    "day_type": {
                        "type": "string",
                        "description": "平日 or 假日",
                    },
                },
                "required": [
                    "employee_id",
                    "nickname",
                    "start_time",
                    "end_time",
                    "hours",
                    "section",
                    "day_type",
                ],
            },
        },
        "page_notes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Handwritten store-wide notes below the table",
        },
    },
    "required": ["date", "weekday", "rows", "page_notes"],
}

SYSTEM_PROMPT = """You extract shift roster data from scanned PDF pages of Ambassador Theatres (國賓影城) branch daily rosters.

Rules:
- Read the page header for date (班別日期) and weekday.
- Extract every employee row with columns: 員工代號, 暱稱, 開始, 結束, 時數.
- Section headers like 平日售票部, 假日樓層 define day_type (平日/假日) and section (售票部/樓層).
- Times must be 24-hour HH:mm format.
- If this page continues the same date as a previous page, set date to null.
- page_notes: only handwritten notes below the table (store-wide reminders), not table rows.
- Do not invent employees or times. If unreadable, omit the row.
"""

USER_PROMPT = """Extract all shift rows from this roster page. Return JSON matching the schema."""
