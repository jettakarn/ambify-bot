"""Gemini vision extractor implementation."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

from google import genai
from google.genai import types

from rostersync.extract.prompt import PAGE_EXTRACTION_SCHEMA, SYSTEM_PROMPT, USER_PROMPT
from rostersync.models import PageExtraction, RosterRow


DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiExtractor:
    """Extract roster pages using Google Gemini vision."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "GEMINI_API_KEY is required for scanned PDF extraction. "
                "Set it in .env or pass --api-key."
            )
        self.model = model or os.environ.get("ROSTERSYNC_GEMINI_MODEL", DEFAULT_MODEL)
        self.client = genai.Client(api_key=key)

    def extract_page(self, image_path: Path) -> PageExtraction:
        image_bytes = image_path.read_bytes()
        suffix = image_path.suffix.lower()
        mime_type = "image/png" if suffix == ".png" else "image/jpeg"

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                USER_PROMPT,
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=PAGE_EXTRACTION_SCHEMA,
                temperature=0,
            ),
        )

        raw = response.text or "{}"
        payload = json.loads(raw)
        return _parse_page_payload(payload)


def _parse_page_payload(payload: dict) -> PageExtraction:
    date_value = payload.get("date")
    parsed_date: dt.date | None = None
    if date_value:
        parsed_date = dt.date.fromisoformat(str(date_value))

    rows = [
        RosterRow.model_validate(row)
        for row in payload.get("rows", [])
    ]

    return PageExtraction(
        date=parsed_date,
        weekday=str(payload.get("weekday") or ""),
        rows=rows,
        page_notes=[str(note) for note in payload.get("page_notes", [])],
    )
