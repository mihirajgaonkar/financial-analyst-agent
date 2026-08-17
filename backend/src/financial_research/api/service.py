from collections.abc import Iterator
import logging
from time import sleep

from financial_research.graph import run_research_graph
from financial_research.agents.research_agent import RESEARCH_SYSTEM_PROMPT
from financial_research.config.settings import get_settings
from financial_research.debug.recorder import capture_external_responses
from financial_research.debug.report_writer import write_debug_report
from financial_research.schemas.company import CompanyInfo
from financial_research.schemas.reports import ResearchReport
from financial_research.services.market_data import get_market_data_provider
from financial_research.services.sec import SECService
from financial_research.storage.file_archive import persist_research_run_files
from financial_research.storage.persistence import persist_research_run

logger = logging.getLogger(__name__)


def run_research(ticker: str, question: str, job_id: str | None = None) -> ResearchReport:
    with capture_external_responses() as external_responses:
        result = run_research_graph(ticker=ticker, research_question=question)
    report = result.get("final_report")
    if report is None:
        raise RuntimeError("Research graph did not produce a final report.")
    settings = get_settings()
    if settings.debug_reports_enabled:
        write_debug_report(
            result,
            ticker=ticker,
            question=question,
            job_id=job_id,
            output_dir=settings.debug_reports_dir,
            system_prompt=RESEARCH_SYSTEM_PROMPT,
            external_responses=external_responses,
        )
    file_archive_dir = None
    try:
        file_archive_dir = persist_research_run_files(
            ticker=ticker,
            question=question,
            state=result,
            report=report,
            external_responses=external_responses,
            job_id=job_id,
            settings=settings,
        )
    except Exception:
        logger.exception("Failed to write file archive for %s.", ticker.upper())
    if settings.database_persistence_enabled:
        try:
            persist_research_run(
                ticker=ticker,
                question=question,
                state=result,
                report=report,
                external_responses=external_responses,
                file_archive_dir=file_archive_dir,
            )
        except Exception:
            logger.exception("Failed to persist research run for %s.", ticker.upper())
    return report


def stream_research_events(ticker: str, question: str) -> Iterator[tuple[str, str]]:
    events = [
        ("research_started", f"Starting research for {ticker.upper()}"),
        ("fetching_sec_data", "Fetching SEC data when requested by the graph"),
        ("fetching_market_data", "Fetching market data when requested by the graph"),
        ("calculating_metrics", "Running deterministic calculation tools"),
        ("generating_analysis", "Generating analysis with the research agent"),
    ]
    for event, data in events:
        yield event, data
        sleep(0.01)
    report = run_research(ticker, question)
    yield "verification_complete", "Verification completed"
    yield "finished", report.model_dump_json()


def get_company(ticker: str) -> CompanyInfo:
    ticker = ticker.upper()
    try:
        overview = get_market_data_provider().get_company_overview(ticker)
    except Exception:
        cik = SECService().get_company_cik(ticker)
        submissions = SECService().get_company_submissions(cik)
        return CompanyInfo(ticker=ticker, cik=cik, name=submissions.get("name", ticker))
    return overview
