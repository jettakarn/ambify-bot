"""Interactive CLI prompts."""

from __future__ import annotations

import typer


def prompt_employee(employees: list[tuple[str, str]]) -> tuple[str, str | None]:
    """Prompt the user to pick an employee from a numbered list."""
    if not employees:
        typer.secho("班表內找不到任何員工。", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if len(employees) == 1:
        nickname, emp_id = employees[0]
        typer.echo(f"僅一位員工，自動選取：{nickname} ({emp_id})")
        return nickname, emp_id

    typer.echo("\n請選擇員工：")
    for index, (nickname, emp_id) in enumerate(employees, start=1):
        typer.echo(f"  {index}. {nickname} ({emp_id})")

    while True:
        choice = typer.prompt("請輸入編號", type=int)
        if 1 <= choice <= len(employees):
            nickname, emp_id = employees[choice - 1]
            return nickname, emp_id
        typer.secho(f"請輸入 1 到 {len(employees)} 之間的數字。", fg=typer.colors.YELLOW)
