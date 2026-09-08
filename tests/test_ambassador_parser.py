"""Tests for Ambassador page parser with synthetic OCR boxes."""

import datetime as dt

from twoshiftly.extract.ambassador.page_parser import parse_ambassador_page
from twoshiftly.extract.ocr import OcrBox


def _box(text: str, x: float, y: float) -> OcrBox:
    return OcrBox(text=text, x=x, y=y, confidence=0.99)


def test_parse_ambassador_page_extracts_row():
    width, height = 2480, 3507
    boxes = [
        _box("班別日期: 2026/8/21 星期五", 800, 365),
        _box("平日售票部", 224, 552),
        _box("1324401", 240, 1720),
        _box("Jetson", 416, 1720),
        _box("17:00", 566, 1720),
        _box("01:00", 724, 1720),
        _box("08:00", 886, 1720),
    ]
    result = parse_ambassador_page(boxes, page_width=width, page_height=height)
    assert result.date == dt.date(2026, 8, 21)
    assert result.weekday == "星期五"
    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.employee_id == "1324401"
    assert row.nickname == "Jetson"
    assert row.start_time == "17:00"
    assert row.end_time == "01:00"
    assert row.hours == "08:00"
    assert row.section == "售票部"
    assert row.day_type == "平日"


def test_parse_ambassador_page_trainer_and_floor_sections():
    width, height = 2480, 3507
    boxes = [
        _box("班別日期: 2026/8/22 星期六", 800, 365),
        _box("假日訓練員", 120, 560),
        _box("1325001", 240, 700),
        _box("Alex", 416, 700),
        _box("10:00", 566, 700),
        _box("18:00", 724, 700),
        _box("08:00", 886, 700),
        _box("樓層", 100, 900),
        _box("1325002", 240, 1100),
        _box("Blair", 416, 1100),
        _box("12:00", 566, 1100),
        _box("20:00", 724, 1100),
        _box("08:00", 886, 1100),
    ]
    result = parse_ambassador_page(boxes, page_width=width, page_height=height)
    assert len(result.rows) == 2
    assert result.rows[0].nickname == "Alex"
    assert result.rows[0].section == "訓練員"
    assert result.rows[0].day_type == "假日"
    assert result.rows[1].nickname == "Blair"
    assert result.rows[1].section == "樓層"
