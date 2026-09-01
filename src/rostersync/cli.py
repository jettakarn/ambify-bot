"""Command-line interface for rostersync."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from dotenv import load_dotenv

from rostersync.models import EmployeeSchedule, RosterDocument
from rostersync.pdf.probe import probe_pdf
from rostersync.service import load_roster_document
from rostersync.transform.filter import filter_employee_schedule, list_employees
from rostersync.transform.ics import build_ics

app = typer.Typer(
    name="rostersync",
    help="Convert PDF shift rosters to calendar (.ics) files.",
    no_args_is_help=True,
)


def _load_env() -> None:
    load_dotenv()


def _default_output_path(pdf_path: Path, employee: str, suffix: str) -> Path:
    stem = pdf_path.stem
    safe_name = employee.lower().replace(" ", "-")
    return pdf_path.parent / f"{safe_name}-{stem}{suffix}"


def _write_json(path: Path, schedule: EmployeeSchedule) -> None:
    payload = schedule.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_ics(path: Path, schedule: EmployeeSchedule) -> None:
    path.write_bytes(build_ics(schedule).encode("utf-8"))


def _write_document_json(path: Path, document: RosterDocument) -> None:
    path.write_text(
        document.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )


@app.command("convert")
def convert(
    pdf: Annotated[Path, typer.Argument(help="Path to roster PDF", exists=True, dir_okay=False)],
    employee: Annotated[Optional[str], typer.Option("--employee", "-e", help="Employee nickname")] = None,
    employee_id: Annotated[Optional[str], typer.Option("--employee-id", help="Employee ID")] = None,
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Output .ics path")] = None,
    provider: Annotated[str, typer.Option("--provider", help="Vision provider for scanned PDFs")] = "gemini",
    model: Annotated[Optional[str], typer.Option("--model", help="Vision model name")] = None,
    api_key: Annotated[Optional[str], typer.Option("--api-key", help="Vision API key")] = None,
    strict: Annotated[bool, typer.Option("--strict", help="Fail on validation errors")] = False,
    infer_days_off: Annotated[bool, typer.Option("--infer-days-off/--no-infer-days-off")] = True,
    cache_dir: Annotated[Optional[Path], typer.Option("--cache-dir", help="Vision cache directory")] = None,
    render_dir: Annotated[Optional[Path], typer.Option("--render-dir", help="Rendered page directory")] = None,
    target_width: Annotated[int, typer.Option("--target-width", help="Rendered page width in px")] = 1700,
    also_json: Annotated[bool, typer.Option("--also-json", help="Also write JSON output")] = False,
) -> None:
    """Convert a roster PDF to an employee .ics calendar file."""
    _load_env()

    document, issues = load_roster_document(
        pdf,
        provider=provider,
        api_key=api_key,
        model=model,
        cache_dir=cache_dir,
        render_dir=render_dir,
        target_width=target_width,
        strict=strict,
    )

    for issue in issues:
        typer.echo(f"[{issue.level}] {issue.message}", err=True)

    schedule = filter_employee_schedule(
        document,
        employee=employee,
        employee_id=employee_id,
        infer_days_off=infer_days_off,
    )

    resolved_name = schedule.employee_name
    ics_path = output or _default_output_path(pdf, resolved_name, ".ics")
    _write_ics(ics_path, schedule)
    typer.echo(f"Wrote {ics_path}")

    if also_json:
        json_path = ics_path.with_suffix(".json")
        _write_json(json_path, schedule)
        typer.echo(f"Wrote {json_path}")


@app.command("extract")
def extract(
    pdf: Annotated[Path, typer.Argument(help="Path to roster PDF", exists=True, dir_okay=False)],
    json_out: Annotated[Optional[Path], typer.Option("--json", "-j", help="Output JSON path")] = None,
    provider: Annotated[str, typer.Option("--provider")] = "gemini",
    model: Annotated[Optional[str], typer.Option("--model")] = None,
    api_key: Annotated[Optional[str], typer.Option("--api-key")] = None,
    strict: Annotated[bool, typer.Option("--strict")] = False,
    cache_dir: Annotated[Optional[Path], typer.Option("--cache-dir")] = None,
    render_dir: Annotated[Optional[Path], typer.Option("--render-dir")] = None,
    target_width: Annotated[int, typer.Option("--target-width")] = 1700,
) -> None:
    """Extract full roster document to JSON without filtering by employee."""
    _load_env()

    document, issues = load_roster_document(
        pdf,
        provider=provider,
        api_key=api_key,
        model=model,
        cache_dir=cache_dir,
        render_dir=render_dir,
        target_width=target_width,
        strict=strict,
    )

    for issue in issues:
        typer.echo(f"[{issue.level}] {issue.message}", err=True)

    out_path = json_out or pdf.with_suffix(".roster.json")
    _write_document_json(out_path, document)
    typer.echo(f"Wrote {out_path}")
    typer.echo(f"Days: {len(document.days)}")


@app.command("inspect")
def inspect(
    pdf: Annotated[Path, typer.Argument(help="Path to roster PDF", exists=True, dir_okay=False)],
    provider: Annotated[str, typer.Option("--provider")] = "gemini",
    model: Annotated[Optional[str], typer.Option("--model")] = None,
    api_key: Annotated[Optional[str], typer.Option("--api-key")] = None,
    cache_dir: Annotated[Optional[Path], typer.Option("--cache-dir")] = None,
    render_dir: Annotated[Optional[Path], typer.Option("--render-dir")] = None,
    target_width: Annotated[int, typer.Option("--target-width")] = 1700,
) -> None:
    """Show PDF metadata and employee list without writing output files."""
    _load_env()

    probe = probe_pdf(pdf)
    typer.echo(f"File: {pdf}")
    typer.echo(f"Pages: {probe.page_count}")
    typer.echo(f"Text layer: {'yes' if probe.has_text_layer else 'no (vision required)'}")

    document, issues = load_roster_document(
        pdf,
        provider=provider,
        api_key=api_key,
        model=model,
        cache_dir=cache_dir,
        render_dir=render_dir,
        target_width=target_width,
        strict=False,
    )

    if document.date_range:
        start, end = document.date_range
        typer.echo(f"Dates: {start.isoformat()} .. {end.isoformat()}")

    typer.echo(f"Days extracted: {len(document.days)}")
    typer.echo(f"Validation issues: {len(issues)}")

    employees = list_employees(document)
    typer.echo("Employees:")
    for nickname, emp_id in employees:
        typer.echo(f"  - {nickname} ({emp_id})")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
