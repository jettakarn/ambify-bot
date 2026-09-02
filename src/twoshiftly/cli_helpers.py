"""Shared CLI helpers for document loading and feedback."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import typer

from twoshiftly.models import RosterDocument, ValidationIssue
from twoshiftly.pdf.render import DEFAULT_RENDER_WIDTH
from twoshiftly.service import load_roster_document


def load_document_with_feedback(
    pdf_path: Path,
    *,
    cache_dir: Path | None = None,
    render_dir: Path | None = None,
    target_width: int = DEFAULT_RENDER_WIDTH,
    strict: bool = False,
    on_page: Callable[[int, int], None] | None = None,
) -> tuple[RosterDocument, list[ValidationIssue]]:
    """Load roster and print validation issues."""
    document, issues = load_roster_document(
        pdf_path,
        cache_dir=cache_dir,
        render_dir=render_dir,
        target_width=target_width,
        strict=strict,
        on_page=on_page,
    )

    for issue in issues:
        typer.echo(f"[{issue.level}] {issue.message}", err=True)

    return document, issues


def default_page_progress(current: int, total: int) -> None:
    """Print page extraction progress."""
    typer.echo(f"正在讀取第 {current}/{total} 頁...")
