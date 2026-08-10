from collections.abc import Iterator
from time import sleep

from financial_research.graph import run_research_graph
from financial_research.schemas.company import CompanyInfo
from financial_research.schemas.reports import ResearchReport
from financial_research.services.market_data import get_market_data_provider
from financial_research.services.sec import SECService


def run_research(ticker: str, question: str) -> ResearchReport:
    result = run_research_graph(ticker=ticker, research_question=question)
    report = result.get("final_report")
    if report is None:
        raise RuntimeError("Research graph did not produce a final report.")
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
