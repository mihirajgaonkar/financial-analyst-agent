from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException

from financial_research.api.job_store import job_store
from financial_research.api.routes.research import _run_and_store_job
from financial_research.api.schemas import ChatRequest, ChatResponse, ThreadResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, background_tasks: BackgroundTasks) -> ChatResponse:
    thread_id = request.thread_id or str(uuid4())
    job = job_store.create_job(request.ticker, request.question)
    job_store.attach_job_to_thread(thread_id, job.job_id)
    background_tasks.add_task(_run_and_store_job, job.job_id, request.ticker, request.question)
    return ChatResponse(thread_id=thread_id, job=job)


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
def get_thread(thread_id: str) -> ThreadResponse:
    jobs = job_store.get_thread_jobs(thread_id)
    if not jobs:
        raise HTTPException(status_code=404, detail="Thread not found.")
    return ThreadResponse(thread_id=thread_id, jobs=jobs)
