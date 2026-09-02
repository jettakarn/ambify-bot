"""Disk cache for page extraction results."""

from __future__ import annotations

import json
from pathlib import Path

from twoshiftly.models import PageExtraction


class ExtractionCache:
    """Cache page extractions keyed by image content hash."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, content_hash: str) -> Path:
        return self.cache_dir / f"{content_hash}.json"

    def get(self, content_hash: str) -> PageExtraction | None:
        path = self._path_for(content_hash)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return PageExtraction.model_validate(data)

    def set(self, content_hash: str, extraction: PageExtraction) -> None:
        path = self._path_for(content_hash)
        path.write_text(
            extraction.model_dump_json(indent=2),
            encoding="utf-8",
        )
