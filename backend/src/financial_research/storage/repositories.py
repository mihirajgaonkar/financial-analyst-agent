from datetime import date, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from financial_research.schemas.company import CompanyInfo
from financial_research.schemas.financials import FinancialMetric
from financial_research.schemas.reports import ResearchReport, ResearchSource
from financial_research.storage.models import (
    Company,
    FilingChunk,
    ResearchJob,
    SourceMetadata,
    StoredGraphTrace,
    StoredFinancialMetric,
    StoredProviderResponse,
    StoredResearchReport,
)


class CompanyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, company_info: CompanyInfo) -> Company:
        ticker = company_info.ticker.upper()
        company = self.session.scalar(select(Company).where(Company.ticker == ticker))
        if company is None:
            company = Company(ticker=ticker, name=company_info.name)
            self.session.add(company)
        company.cik = company_info.cik
        company.name = company_info.name
        company.exchange = company_info.exchange
        company.sector = company_info.sector
        company.industry = company_info.industry
        self.session.flush()
        return company

    def get_by_ticker(self, ticker: str) -> Company | None:
        return self.session.scalar(select(Company).where(Company.ticker == ticker.upper()))


class ResearchJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, ticker: str, question: str, company_id: int | None = None) -> ResearchJob:
        job = ResearchJob(ticker=ticker.upper(), question=question, company_id=company_id)
        self.session.add(job)
        self.session.flush()
        return job

    def mark_complete(self, job: ResearchJob) -> ResearchJob:
        job.status = "complete"
        job.completed_at = datetime.now().astimezone()
        self.session.flush()
        return job


class ReportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, report: ResearchReport, job_id: int | None = None) -> StoredResearchReport:
        stored = StoredResearchReport(ticker=report.ticker.upper(), job_id=job_id, report_json=report.model_dump(mode="json"))
        self.session.add(stored)
        self.session.flush()
        return stored


class GraphTraceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, ticker: str, state: dict[str, Any], job_id: int | None = None) -> StoredGraphTrace:
        messages = state.get("messages", [])
        tool_results = state.get("tool_results", [])
        stored = StoredGraphTrace(
            ticker=ticker.upper(),
            job_id=job_id,
            state_json=_jsonable({key: value for key, value in state.items() if key != "messages"}),
            messages_json=_jsonable(messages),
            tool_results_json=_jsonable(tool_results),
        )
        self.session.add(stored)
        self.session.flush()
        return stored


class ProviderResponseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_many(
        self,
        responses: list[dict[str, Any]],
        job_id: int | None = None,
        *,
        file_paths: list[str | None] | None = None,
        store_payloads: bool = True,
    ) -> list[StoredProviderResponse]:
        file_paths = file_paths or [None] * len(responses)
        stored_responses = [
            StoredProviderResponse(
                job_id=job_id,
                provider=response.get("provider", "unknown"),
                url=response.get("url", ""),
                params_json=_jsonable(response.get("params", {})),
                payload_file_path=file_paths[index] if index < len(file_paths) else None,
                payload_json=_jsonable(response.get("payload")) if store_payloads else None,
            )
            for index, response in enumerate(responses)
        ]
        self.session.add_all(stored_responses)
        self.session.flush()
        return stored_responses


class FinancialMetricRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_many(self, ticker: str, metrics: list[FinancialMetric]) -> list[StoredFinancialMetric]:
        stored_metrics = [
            StoredFinancialMetric(
                ticker=ticker.upper(),
                name=metric.name,
                value=metric.value,
                unit=metric.unit,
                period=metric.period,
                source=metric.source,
                calculated=metric.calculated,
                inputs=metric.inputs,
            )
            for metric in metrics
        ]
        self.session.add_all(stored_metrics)
        self.session.flush()
        return stored_metrics


class SourceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_many(self, sources: list[ResearchSource]) -> list[SourceMetadata]:
        stored_sources = [
            SourceMetadata(
                source_type=source.source_type,
                title=source.title,
                url=source.url,
                retrieved_at=source.retrieved_at,
            )
            for source in sources
        ]
        self.session.add_all(stored_sources)
        self.session.flush()
        return stored_sources


class FilingChunkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_many(self, chunks: list[dict]) -> list[FilingChunk]:
        stored_chunks = [FilingChunk(**chunk) for chunk in chunks]
        self.session.add_all(stored_chunks)
        self.session.flush()
        return stored_chunks

    def search_by_metadata(self, ticker: str, section: str | None = None, limit: int = 10) -> list[FilingChunk]:
        query = select(FilingChunk).where(FilingChunk.ticker == ticker.upper())
        if section:
            query = query.where(FilingChunk.section == section)
        return list(self.session.scalars(query.limit(limit)))


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    return value
