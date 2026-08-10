from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from pydantic import field_validator

from financial_research.schemas.company import CompanyInfo
from financial_research.schemas.reports import ResearchReport
from financial_research.middleware.validation import normalize_ticker


class ResearchRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)
    question: str = Field(min_length=1, max_length=2000)
    stream: bool = False

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        return normalize_ticker(value)


class ResearchJobResponse(BaseModel):
    job_id: str
    ticker: str
    question: str
    status: Literal["pending", "running", "complete", "failed"]
    report: ResearchReport | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    ticker: str
    question: str
    thread_id: str | None = None

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        return normalize_ticker(value)


class ChatResponse(BaseModel):
    thread_id: str = Field(default_factory=lambda: str(uuid4()))
    job: ResearchJobResponse


class ThreadResponse(BaseModel):
    thread_id: str
    jobs: list[ResearchJobResponse]


class CompanyResponse(BaseModel):
    company: CompanyInfo
    cik: str | None = None
