"""Vision extractor protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from rostersync.models import PageExtraction


class VisionExtractor(Protocol):
    """Pluggable vision model for scanned roster pages."""

    def extract_page(self, image_path: Path) -> PageExtraction:
        """Extract roster data from one page image."""
        ...
