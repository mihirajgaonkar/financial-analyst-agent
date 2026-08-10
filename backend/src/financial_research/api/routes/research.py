from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from financial_research.api.job_store import job_store
from financial_research.api.schemas import ResearchJobResponse, ResearchRequest
from financial_research.api.service import run_research, stream_research_events

router = APIRouter(tags=["research"])


@router.post("/research", response_model=ResearchJobResponse)
def create_research_job(request: ResearchRequest, background_tasks: BackgroundTasks):
    if request.stream:
        return StreamingResponse(_format_sse(stream_research_events(request.ticker, request.question)), media_type="text/event-stream")
    job = job_store.create_job(request.ticker, request.question)
    background_tasks.add_task(_run_and_store_job, job.job_id, request.ticker, request.question)
    return job


@router.get("/research/{job_id}", response_model=ResearchJobResponse)
def get_research_job(job_id: str) -> ResearchJobResponse:
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Research job not found.")
    return job


def _run_and_store_job(job_id: str, ticker: str, question: str) -> None:
    job_store.update_job(job_id, "running")
    try:
        report = run_research(ticker, question)
    except Exception as exc:
        job_store.update_job(job_id, "failed", error=str(exc))
        return
    job_store.update_job(job_id, "complete", report=report)


def _format_sse(events):
    for event, data in events:
        yield f"event: {event}\ndata: {data}\n\n"
