"""FastAPI server: upload roster PDF, pick employee, download .ics."""

from __future__ import annotations

import tempfile
import threading
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from twoshiftly.service import load_roster_document
from twoshiftly.transform.filter import filter_employee_schedule, list_employees
from twoshiftly.transform.ics import build_ics
from twoshiftly.web.jobs import Job, store

STATIC_DIR = Path(__file__).resolve().parent / "static"
HOST = "127.0.0.1"
PORT = 8765

app = FastAPI(title="2shiftly", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class IcsRequest(BaseModel):
    employee: str | None = None
    employee_id: str | None = None
    infer_days_off: bool = True


class EmployeeOut(BaseModel):
    nickname: str
    employee_id: str


class JobStatusOut(BaseModel):
    job_id: str
    status: str
    current_page: int = 0
    total_pages: int = 0
    date_start: str | None = None
    date_end: str | None = None
    employees: list[EmployeeOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class UploadAccepted(BaseModel):
    job_id: str


def _job_status(job: Job) -> JobStatusOut:
    date_start = date_end = None
    employees: list[EmployeeOut] = []
    warnings: list[str] = []

    if job.document is not None:
        if job.document.date_range:
            start, end = job.document.date_range
            date_start = start.isoformat()
            date_end = end.isoformat()
        employees = [
            EmployeeOut(nickname=name, employee_id=emp_id)
            for name, emp_id in list_employees(job.document)
        ]
        warnings = [issue.message for issue in job.issues]

    return JobStatusOut(
        job_id=job.id,
        status=job.status,
        current_page=job.current_page,
        total_pages=job.total_pages,
        date_start=date_start,
        date_end=date_end,
        employees=employees,
        warnings=warnings,
        error=job.error,
    )


def _process_job(job_id: str) -> None:
    job = store.get(job_id)
    if job is None:
        return

    job.status = "processing"

    def on_page(current: int, total: int) -> None:
        job.current_page = current
        job.total_pages = total

    try:
        document, issues = load_roster_document(
            job.pdf_path,
            cache_dir=job.work_dir / "cache",
            render_dir=job.work_dir / "render",
            strict=False,
            on_page=on_page,
        )
        job.document = document
        job.issues = issues
        job.status = "ready"
    except Exception as exc:  # noqa: BLE001 — surface to UI
        job.error = str(exc)
        job.status = "error"


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.post("/api/upload", response_model=UploadAccepted)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadAccepted:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="請上傳 PDF 檔案。")

    work_dir = Path(tempfile.mkdtemp(prefix="twoshiftly-"))
    pdf_path = work_dir / "roster.pdf"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="檔案是空的。")
    pdf_path.write_bytes(content)

    job = store.create(work_dir, pdf_path)
    background_tasks.add_task(_process_job, job.id)
    return UploadAccepted(job_id=job.id)


@app.get("/api/jobs/{job_id}", response_model=JobStatusOut)
def get_job(job_id: str) -> JobStatusOut:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="找不到這次上傳。")
    return _job_status(job)


@app.get("/api/jobs/{job_id}/progress", response_model=JobStatusOut)
def get_progress(job_id: str) -> JobStatusOut:
    return get_job(job_id)


def _ready_job(job_id: str) -> Job:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="找不到這次上傳。")
    if job.status != "ready" or job.document is None:
        raise HTTPException(status_code=409, detail="班表還沒準備好。")
    return job


def _schedule_from_request(job: Job, body: IcsRequest):
    if not body.employee and not body.employee_id:
        raise HTTPException(status_code=400, detail="請選擇員工。")
    try:
        return filter_employee_schedule(
            job.document,
            employee=body.employee,
            employee_id=body.employee_id,
            infer_days_off=body.infer_days_off,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/jobs/{job_id}/schedule")
def get_schedule(job_id: str, body: IcsRequest) -> dict:
    job = _ready_job(job_id)
    schedule = _schedule_from_request(job, body)
    return schedule.model_dump(mode="json")


@app.post("/api/jobs/{job_id}/ics")
def download_ics(job_id: str, body: IcsRequest) -> Response:
    job = _ready_job(job_id)
    schedule = _schedule_from_request(job, body)

    ics_text = build_ics(schedule)
    safe_name = schedule.employee_name.lower().replace(" ", "-")
    filename = f"{safe_name}-roster.ics"
    return Response(
        content=ics_text.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def main() -> None:
    store.cleanup_expired()
    url = f"http://{HOST}:{PORT}/"

    def _open_browser() -> None:
        webbrowser.open(url)

    timer = threading.Timer(0.8, _open_browser)
    timer.daemon = True
    timer.start()

    print(f"2shiftly running at {url}")
    print("Press Ctrl+C to stop.")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
