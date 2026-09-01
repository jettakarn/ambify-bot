"""Shared pytest fixtures."""

import json
from pathlib import Path

import pytest

from rostersync.models import RosterDocument

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def roster_document() -> RosterDocument:
    data = json.loads((FIXTURES / "roster_anonymized.json").read_text(encoding="utf-8"))
    return RosterDocument.model_validate(data)
