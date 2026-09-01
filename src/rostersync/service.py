"""High-level roster extraction orchestration."""

from __future__ import annotations

from pathlib import Path

from rostersync.extract.base import VisionExtractor
from rostersync.extract.gemini import GeminiExtractor
from rostersync.extract.pipeline import extract_scanned_roster
from rostersync.models import RosterDocument, ValidationIssue
from rostersync.pdf.probe import probe_pdf
from rostersync.pdf.text_tables import extract_text_roster
from rostersync.validate import validate_document


def load_roster_document(
    pdf_path: Path,
    *,
    provider: str = "gemini",
    api_key: str | None = None,
    model: str | None = None,
    cache_dir: Path | None = None,
    render_dir: Path | None = None,
    target_width: int = 1700,
    strict: bool = False,
) -> tuple[RosterDocument, list[ValidationIssue]]:
    """Load and validate a roster document from PDF."""
    probe = probe_pdf(pdf_path)

    if probe.has_text_layer:
        document = extract_text_roster(pdf_path)
    else:
        extractor = _build_extractor(provider, api_key=api_key, model=model)
        document = extract_scanned_roster(
            pdf_path,
            extractor,
            cache_dir=cache_dir,
            render_dir=render_dir,
            target_width=target_width,
        )

    issues = validate_document(document)
    if strict:
        errors = [issue for issue in issues if issue.level == "error"]
        if errors:
            messages = "\n".join(f"- {issue.message}" for issue in errors)
            raise ValueError(f"Validation failed:\n{messages}")

    return document, issues


def _build_extractor(
    provider: str,
    *,
    api_key: str | None,
    model: str | None,
) -> VisionExtractor:
    if provider.lower() == "gemini":
        return GeminiExtractor(api_key=api_key, model=model)
    raise ValueError(f"Unsupported vision provider: {provider}")
