"""Command-line interface for twoshiftly (2shiftly)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from twoshiftly.cli_helpers import default_page_progress, load_document_with_feedback
from twoshiftly.cli_interactive import prompt_employee
from twoshiftly.models import EmployeeSchedule, RosterDocument
from twoshiftly.pdf.render import DEFAULT_RENDER_WIDTH
from twoshiftly.transform.filter import filter_employee_schedule, list_employees
from twoshiftly.transform.ics import build_ics

app = typer.Typer(
    name="twoshiftly",
    help="2shiftly — offline OCR: scanned PDF rosters → calendar (.ics)",
    no_args_is_help=True,
)


def _default_output_path(pdf_path: Path, employee: str, suffix: str) -> Path:
    safe_name = employee.lower().replace(" ", "-")
    return pdf_path.parent / f"{safe_name}-{pdf_path.stem}{suffix}"


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
    strict: Annotated[bool, typer.Option("--strict", help="Fail on validation errors")] = False,
    infer_days_off: Annotated[bool, typer.Option("--infer-days-off/--no-infer-days-off")] = True,
    cache_dir: Annotated[Optional[Path], typer.Option("--cache-dir", help="OCR cache directory")] = None,
    render_dir: Annotated[Optional[Path], typer.Option("--render-dir", help="Rendered page directory")] = None,
    target_width: Annotated[int, typer.Option("--target-width", help="Rendered page width in px")] = DEFAULT_RENDER_WIDTH,
    also_json: Annotated[bool, typer.Option("--also-json", help="Also write JSON output")] = False,
) -> None:
    """Convert a scanned roster PDF to an employee .ics calendar file."""
    typer.echo("twoshiftly — offline OCR mode (no API key)")

    document, _issues = load_document_with_feedback(
        pdf,
        cache_dir=cache_dir,
        render_dir=render_dir,
        target_width=target_width,
        strict=strict,
        on_page=default_page_progress,
    )

    if not employee and not employee_id:
        picked_name, picked_id = prompt_employee(list_employees(document))
        employee = picked_name
        employee_id = picked_id

    schedule = filter_employee_schedule(
        document,
        employee=employee,
        employee_id=employee_id,
        infer_days_off=infer_days_off,
    )

    ics_path = output or _default_output_path(pdf, schedule.employee_name, ".ics")
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
    strict: Annotated[bool, typer.Option("--strict")] = False,
    cache_dir: Annotated[Optional[Path], typer.Option("--cache-dir")] = None,
    render_dir: Annotated[Optional[Path], typer.Option("--render-dir")] = None,
    target_width: Annotated[int, typer.Option("--target-width")] = DEFAULT_RENDER_WIDTH,
) -> None:
    """Extract full roster document to JSON."""
    document, _issues = load_document_with_feedback(
        pdf,
        cache_dir=cache_dir,
        render_dir=render_dir,
        target_width=target_width,
        strict=strict,
        on_page=default_page_progress,
    )

    out_path = json_out or pdf.with_suffix(".roster.json")
    _write_document_json(out_path, document)
    typer.echo(f"Wrote {out_path}")
    typer.echo(f"Days: {len(document.days)}")


@app.command("inspect")
def inspect(
    pdf: Annotated[Path, typer.Argument(help="Path to roster PDF", exists=True, dir_okay=False)],
    cache_dir: Annotated[Optional[Path], typer.Option("--cache-dir")] = None,
    render_dir: Annotated[Optional[Path], typer.Option("--render-dir")] = None,
    target_width: Annotated[int, typer.Option("--target-width")] = DEFAULT_RENDER_WIDTH,
) -> None:
    """Show PDF metadata and employee list."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf))
    typer.echo(f"File: {pdf}")
    typer.echo(f"Pages: {len(doc)}")
    typer.echo("Mode: local OCR (twoshiftly)")

    document, issues = load_document_with_feedback(
        pdf,
        cache_dir=cache_dir,
        render_dir=render_dir,
        target_width=target_width,
        strict=False,
        on_page=default_page_progress,
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
