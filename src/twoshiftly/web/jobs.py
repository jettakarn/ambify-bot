"""In-memory job store for roster upload sessions."""

from __future__ import annotations

import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from twoshiftly.models import RosterDocument, ValidationIssue

JOB_TTL_SECONDS = 60 * 60


@dataclass
class Job:
    id: str
    work_dir: Path
    pdf_path: Path
    status: str = "queued"  # queued | processing | ready | error
    current_page: int = 0
    total_pages: int = 0
    document: RosterDocument | None = None
    issues: list[ValidationIssue] = field(default_factory=list)
    error: str | None = None
    created_at: float = field(default_factory=time.time)


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, work_dir: Path, pdf_path: Path) -> Job:
        self.cleanup_expired()
        job = Job(id=uuid.uuid4().hex, work_dir=work_dir, pdf_path=pdf_path)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def delete(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.pop(job_id, None)
        if job is not None:
            shutil.rmtree(job.work_dir, ignore_errors=True)

    def cleanup_expired(self) -> None:
        now = time.time()
        with self._lock:
            expired = [
                job_id
                for job_id, job in self._jobs.items()
                if now - job.created_at > JOB_TTL_SECONDS
            ]
        for job_id in expired:
            self.delete(job_id)

    def clear_all(self) -> None:
        with self._lock:
            ids = list(self._jobs.keys())
        for job_id in ids:
            self.delete(job_id)


store = JobStore()
