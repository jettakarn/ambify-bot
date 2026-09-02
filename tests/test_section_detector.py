"""Tests for section/time OCR normalization."""

from twoshiftly.extract.ambassador.section_detector import normalize_time, parse_section


def test_normalize_time_fixes_ocr_0060():
    assert normalize_time("00:60") == "09:00"


def test_normalize_time_rejects_invalid_minutes():
    assert normalize_time("12:99") is None


def test_parse_section_ambassador_header():
    assert parse_section("平日售票部") == ("平日", "售票部")
    assert parse_section("假日樓層") == ("假日", "樓層")
