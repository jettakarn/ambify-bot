"""Detect section headers and parse dates from OCR boxes."""

from __future__ import annotations

import datetime as dt
import re

from twoshiftly.extract.ocr import OcrBox

DATE_RE = re.compile(r"(\d{4})\s*[/-]\s*(\d{1,2})\s*[/-]\s*(\d{1,2})")
WEEKDAY_RE = re.compile(r"星期[一二三四五六日天]")
SECTION_RE = re.compile(r"(平日|假日)\s*(售票|樓層)")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
TIME_FIND_RE = re.compile(r"\d{1,2}:\d{2}")
EMPLOYEE_ID_RE = re.compile(r"^\d{3,8}$")

HEADER_KEYWORDS = ("員工代號", "工代號", "暱稱", "開始", "结束", "結束", "時數", "时數", "總時數", "總时數")


def parse_page_date(boxes: list[OcrBox], *, header_y_max: float, page_height: float) -> tuple[dt.date | None, str]:
    """Extract date and weekday from header region."""
    weekday = ""
    parsed_date: dt.date | None = None
    limit = header_y_max * page_height

    header_texts: list[str] = []
    for box in boxes:
        if box.y <= limit:
            header_texts.append(box.text)
            weekday_match = WEEKDAY_RE.search(box.text)
            if weekday_match:
                weekday = weekday_match.group(0)

    joined = " ".join(header_texts)
    match = DATE_RE.search(joined)
    if match:
        year, month, day = map(int, match.groups())
        parsed_date = dt.date(year, month, day)

    return parsed_date, weekday


def parse_section(text: str) -> tuple[str, str] | None:
    """Return (day_type, section) from a section header line."""
    normalized = text.replace("部", "")
    match = SECTION_RE.search(normalized)
    if not match:
        return None
    day_type, section = match.groups()
    section_label = "售票部" if "售票" in section else "樓層"
    return day_type, section_label


def normalize_time(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().replace("：", ":").replace("O", "0").replace("o", "0")
    cleaned = re.sub(r"[^\d:]", "", cleaned)
    if not TIME_RE.match(cleaned):
        return None
    hour, minute = cleaned.split(":")
    h, m = int(hour), int(minute)
    # RapidOCR often reads 09:00 as 00:60 on scanned rosters.
    if h == 0 and m == 60:
        return "09:00"
    if m >= 60 or h >= 24:
        return None
    return f"{h:02d}:{m:02d}"


def is_header_row(texts: list[str]) -> bool:
    joined = "".join(texts)
    return any(keyword in joined for keyword in HEADER_KEYWORDS)


def is_section_row(texts: list[str]) -> bool:
    joined = "".join(texts)
    if parse_section(joined) is not None:
        return True
    return any(k in joined for k in ("總時數", "總时數", "总时数"))


def looks_like_employee_id(text: str) -> bool:
    return bool(EMPLOYEE_ID_RE.match(text.strip()))


def clean_row_cells(cells: dict[str, str]) -> dict[str, str]:
    """Fix common OCR column bleed (times merged into nickname)."""
    cleaned = dict(cells)
    nickname = cleaned.get("nickname", "").strip()
    start = cleaned.get("start_time", "").strip()
    end = cleaned.get("end_time", "").strip()
    hours = cleaned.get("hours", "").strip()

    times_in_nick = TIME_FIND_RE.findall(nickname)
    if times_in_nick:
        if not start:
            start = times_in_nick[0]
        if len(times_in_nick) > 1 and not end:
            end = times_in_nick[1]
        nickname = TIME_FIND_RE.sub("", nickname).strip()

    if TIME_RE.match(nickname) and start:
        nickname, start = start, nickname

    cleaned["nickname"] = nickname
    cleaned["start_time"] = start
    cleaned["end_time"] = end
    cleaned["hours"] = hours
    return cleaned
