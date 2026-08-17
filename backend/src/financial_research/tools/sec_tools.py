from typing import Any

from langchain.tools import tool

from financial_research.config.settings import get_settings
from financial_research.services.sec import parse_company_facts_history, parse_company_facts_metrics, SECService


def create_sec_tools(sec_service: SECService | None = None) -> list:
    service = sec_service or SECService()
    settings = get_settings()

    @tool
    def get_company_profile(ticker: str) -> dict[str, Any]:
        """Resolve a public company ticker to SEC identifiers and submission metadata."""
        cik = service.get_company_cik(ticker)
        submissions = service.get_company_submissions(cik)
        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "company_name": submissions.get("name"),
            "sic": submissions.get("sic"),
            "sic_description": submissions.get("sicDescription"),
            "fiscal_year_end": submissions.get("fiscalYearEnd"),
            "exchanges": submissions.get("exchanges", []),
        }

    @tool
    def get_latest_10k(ticker: str) -> dict[str, Any] | None:
        """Fetch metadata and SEC URL for the latest 10-K filing for a ticker."""
        cik = service.get_company_cik(ticker)
        filing = service.get_latest_10k(cik)
        return filing.model_dump(mode="json") if filing else None

    @tool
    def get_latest_10q(ticker: str) -> dict[str, Any] | None:
        """Fetch metadata and SEC URL for the latest 10-Q filing for a ticker."""
        cik = service.get_company_cik(ticker)
        filing = service.get_latest_10q(cik)
        return filing.model_dump(mode="json") if filing else None

    @tool
    def get_company_facts(ticker: str) -> dict[str, Any]:
        """Fetch SEC company facts and return a compact snapshot of common reported GAAP values."""
        cik = service.get_company_cik(ticker)
        facts = service.get_company_facts(cik)
        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "facts": parse_company_facts_metrics(ticker, facts),
            "historical_facts": parse_company_facts_history(facts, limit=settings.sec_company_facts_history_limit),
            "source_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        }

    return [get_company_profile, get_latest_10k, get_latest_10q, get_company_facts]
