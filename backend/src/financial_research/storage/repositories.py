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
    StoredFinancialMetric,
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
