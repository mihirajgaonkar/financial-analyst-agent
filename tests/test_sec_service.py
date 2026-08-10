import httpx
import pytest

from financial_research.config.settings import Settings
from financial_research.services.exceptions import ExternalServiceError, InvalidTickerError
from financial_research.services.sec import (
    SECService,
    parse_company_facts_metrics,
    parse_recent_filings,
)


def test_ticker_to_cik_handling() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"0": {"ticker": "AAPL", "cik_str": 320193, "title": "Apple Inc."}})

    service = SECService(settings=Settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert service.get_company_cik("aapl") == "0000320193"


def test_invalid_ticker_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    service = SECService(settings=Settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(InvalidTickerError):
        service.get_company_cik("NOPE")


def test_recent_filings_parse_to_models() -> None:
    filings = parse_recent_filings(
        "0000320193",
        {
            "accessionNumber": ["0000320193-25-000001"],
            "form": ["10-K"],
            "filingDate": ["2025-10-31"],
            "reportDate": ["2025-09-27"],
            "primaryDocument": ["aapl-20250927.htm"],
        },
    )
    assert filings[0].form == "10-K"
    assert filings[0].url == "https://www.sec.gov/Archives/edgar/data/320193/000032019325000001/aapl-20250927.htm"


def test_company_facts_parsing() -> None:
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [{"end": "2024-09-30", "val": 100}, {"end": "2025-09-30", "val": 125}]}},
                "NetIncomeLoss": {"units": {"USD": [{"end": "2025-09-30", "val": 20}]}},
            }
        }
    }
    assert parse_company_facts_metrics("AAPL", facts) == {"revenue": 125.0, "net_income": 20.0}


def test_sec_http_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server error"})

    service = SECService(settings=Settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ExternalServiceError):
        service.get_company_submissions("0000320193")
