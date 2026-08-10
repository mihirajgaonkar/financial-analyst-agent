from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from financial_research.api.schemas import ResearchJobResponse
from financial_research.schemas.reports import ResearchReport


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, ResearchJobResponse] = {}
        self._threads: dict[str, list[str]] = {}
        self._lock = Lock()

    def create_job(self, ticker: str, question: str, thread_id: str | None = None) -> ResearchJobResponse:
        job = ResearchJobResponse(job_id=str(uuid4()), ticker=ticker.upper(), question=question, status="pending")
        with self._lock:
            self._jobs[job.job_id] = job
            if thread_id:
                self._threads.setdefault(thread_id, []).append(job.job_id)
        return job

    def update_job(
        self,
        job_id: str,
        status: str,
        report: ResearchReport | None = None,
        error: str | None = None,
    ) -> ResearchJobResponse:
        with self._lock:
            job = self._jobs[job_id]
            updated = job.model_copy(
                update={
                    "status": status,
                    "report": report if report is not None else job.report,
                    "error": error,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._jobs[job_id] = updated
            return updated

    def get_job(self, job_id: str) -> ResearchJobResponse | None:
        with self._lock:
            return self._jobs.get(job_id)

    def get_thread_jobs(self, thread_id: str) -> list[ResearchJobResponse]:
        with self._lock:
            return [self._jobs[job_id] for job_id in self._threads.get(thread_id, []) if job_id in self._jobs]

    def attach_job_to_thread(self, thread_id: str, job_id: str) -> None:
        with self._lock:
            self._threads.setdefault(thread_id, []).append(job_id)


job_store = InMemoryJobStore()
