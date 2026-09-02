"""High-level roster extraction orchestration."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from twoshiftly.extract.pipeline import extract_scanned_roster
from twoshiftly.models import RosterDocument, ValidationIssue
from twoshiftly.pdf.render import DEFAULT_RENDER_WIDTH
from twoshiftly.validate import validate_document


def load_roster_document(
    pdf_path: Path,
    *,
    cache_dir: Path | None = None,
    render_dir: Path | None = None,
    target_width: int = DEFAULT_RENDER_WIDTH,
    strict: bool = False,
    on_page: Callable[[int, int], None] | None = None,
) -> tuple[RosterDocument, list[ValidationIssue]]:
    """Load and validate a scanned roster PDF."""
    document = extract_scanned_roster(
        pdf_path,
        cache_dir=cache_dir,
        render_dir=render_dir,
        target_width=target_width,
        on_page=on_page,
    )

    issues = validate_document(document)
    if strict:
        errors = [issue for issue in issues if issue.level == "error"]
        if errors:
            messages = "\n".join(f"- {issue.message}" for issue in errors)
            raise ValueError(f"Validation failed:\n{messages}")

    return document, issues
