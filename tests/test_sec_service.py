import httpx
import pytest

from financial_research.config.settings import Settings
from financial_research.services.exceptions import ExternalServiceError, InvalidTickerError
from financial_research.services.sec import (
    SECService,
    parse_company_facts_metrics,
    parse_company_facts_history,
    parse_recent_filings,
)


def test_ticker_to_cik_handling() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"0": {"ticker": "AAPL", "cik_str": 320193, "title": "Apple Inc."}})

    service = SECService(settings=Settings(provider_cache_enabled=False), client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert service.get_company_cik("aapl") == "0000320193"


def test_sec_service_reuses_cached_provider_response(tmp_path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"name": "Apple Inc."})

    service = SECService(
        settings=Settings(provider_cache_dir=str(tmp_path), provider_cache_enabled=True),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert service.get_company_submissions("0000320193")["name"] == "Apple Inc."
    assert service.get_company_submissions("0000320193")["name"] == "Apple Inc."
    assert calls == 1


def test_invalid_ticker_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    service = SECService(settings=Settings(provider_cache_enabled=False), client=httpx.Client(transport=httpx.MockTransport(handler)))
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

    service = SECService(settings=Settings(provider_cache_enabled=False), client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ExternalServiceError):
        service.get_company_submissions("0000320193")


def test_company_facts_history_returns_annual_periods() -> None:
    facts = {
        "facts": {"us-gaap": {"Revenues": {"units": {"USD": [
            {"end": "2024-09-30", "val": 100, "form": "10-K", "fp": "FY"},
            {"end": "2025-09-30", "val": 125, "form": "10-K", "fp": "FY"},
            {"end": "2026-03-31", "val": 40, "form": "10-Q", "fp": "Q3"},
        ]}}}}
    }
    assert [item["value"] for item in parse_company_facts_history(facts)["revenue"]] == [125.0, 100.0]


def test_company_facts_history_limits_model_facing_periods() -> None:
    facts = {
        "facts": {"us-gaap": {"Revenues": {"units": {"USD": [
            {"end": f"202{year}-12-31", "val": year, "form": "10-K", "fp": "FY"}
            for year in range(6)
        ]}}}}
    }

    history = parse_company_facts_history(facts, limit=3)["revenue"]

    assert len(history) == 3
    assert [item["end"] for item in history] == ["2025-12-31", "2024-12-31", "2023-12-31"]


def test_company_facts_selects_newest_compatible_revenue_concept() -> None:
    facts = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {"USD": [
                        {"end": "2022-01-30", "val": 26_914, "form": "10-K", "fp": "FY"},
                        {"end": "2021-01-31", "val": 16_675, "form": "10-K", "fp": "FY"},
                    ]}
                },
                "Revenues": {
                    "units": {"USD": [
                        {"end": "2026-01-25", "val": 215_000, "form": "10-K", "fp": "FY"},
                        {"end": "2025-01-26", "val": 130_000, "form": "10-K", "fp": "FY"},
                    ]}
                },
            }
        }
    }

    assert parse_company_facts_metrics("NVDA", facts)["revenue"] == 215_000.0
    assert parse_company_facts_history(facts)["revenue"][0]["end"] == "2026-01-25"
