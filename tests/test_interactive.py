"""Tests for interactive employee selection."""

from unittest.mock import patch

import pytest
import typer

from twoshiftly.cli_interactive import prompt_employee


def test_prompt_employee_single_auto_select():
    result = prompt_employee([("Jetson", "1324401")])
    assert result == ("Jetson", "1324401")


def test_prompt_employee_empty_exits():
    with pytest.raises(typer.Exit):
        prompt_employee([])


def test_prompt_employee_multiple_choice():
    employees = [("Ben", "1326502"), ("Jetson", "1324401")]
    with patch("twoshiftly.cli_interactive.typer.prompt", return_value=2):
        result = prompt_employee(employees)
    assert result == ("Jetson", "1324401")
