from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from financial_research.schemas.company import CompanyInfo
from financial_research.schemas.financials import FinancialMetric
from financial_research.schemas.reports import ResearchReport, ResearchSource
from financial_research.storage.models import Base
from financial_research.storage.repositories import (
    CompanyRepository,
    FilingChunkRepository,
    FinancialMetricRepository,
    ReportRepository,
    ResearchJobRepository,
    SourceRepository,
)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_company_upsert_and_job_report_storage() -> None:
    session = make_session()
    company = CompanyRepository(session).upsert(CompanyInfo(ticker="msft", cik="0000789019", name="Microsoft"))
    job = ResearchJobRepository(session).create("msft", "Analyze revenue.", company_id=company.id)
    report = ResearchReport(ticker="MSFT", company_name="Microsoft", reported_facts=["Revenue reported."])
    stored = ReportRepository(session).save(report, job_id=job.id)
    session.commit()

    assert CompanyRepository(session).get_by_ticker("MSFT").id == company.id
    assert stored.report_json["ticker"] == "MSFT"


def test_metric_source_and_filing_chunk_storage() -> None:
    session = make_session()
    metrics = [FinancialMetric(name="revenue_growth", value=0.2, period="FY2025", inputs={"current": 120, "prior": 100})]
    stored_metrics = FinancialMetricRepository(session).save_many("AAPL", metrics)
    sources = [ResearchSource(source_type="sec", title="10-K", url="https://www.sec.gov/filing")]
    stored_sources = SourceRepository(session).save_many(sources)
    chunks = FilingChunkRepository(session).save_many(
        [
            {
                "ticker": "AAPL",
                "cik": "0000320193",
                "accession_number": "1",
                "filing_type": "10-K",
                "filing_date": "2025-10-31",
                "fiscal_period": "FY2025",
                "section": "risk_factors",
                "chunk_index": 0,
                "text": "Risk factor text",
                "source_url": "https://www.sec.gov/filing",
                "embedding": [0.1, 0.2],
            }
        ]
    )
    found_chunks = FilingChunkRepository(session).search_by_metadata("aapl", section="risk_factors")

    assert stored_metrics[0].name == "revenue_growth"
    assert stored_sources[0].title == "10-K"
    assert chunks[0].embedding == [0.1, 0.2]
    assert found_chunks[0].text == "Risk factor text"
