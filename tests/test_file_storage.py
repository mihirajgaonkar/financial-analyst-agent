import json
from datetime import datetime, timedelta, timezone

from langchain_core.messages import HumanMessage

from financial_research.config.settings import Settings
from financial_research.schemas.reports import ResearchReport
from financial_research.storage.file_archive import persist_research_run_files
from financial_research.storage.file_cache import get_cached_provider_response, store_provider_response


def test_provider_cache_stores_and_reuses_payload_without_key_in_cache_lookup(tmp_path) -> None:
    settings = Settings(provider_cache_dir=str(tmp_path), provider_cache_enabled=True)
    url = "https://www.alphavantage.co/query"
    first_params = {"function": "GLOBAL_QUOTE", "symbol": "MSFT", "apikey": "first"}
    second_params = {"function": "GLOBAL_QUOTE", "symbol": "MSFT", "apikey": "second"}
    payload = {"Global Quote": {"05. price": "100"}}

    store_provider_response("Alpha Vantage", url, first_params, payload, settings=settings)

    assert get_cached_provider_response("Alpha Vantage", url, second_params, ttl_seconds=900, settings=settings) == payload


def test_provider_cache_respects_ttl(tmp_path) -> None:
    settings = Settings(provider_cache_dir=str(tmp_path), provider_cache_enabled=True)
    store_provider_response("SEC", "https://data.sec.gov/submissions/CIK1.json", None, {"ok": True}, settings=settings)
    cache_file = next((tmp_path / "sec").glob("*.json"))
    old = datetime.now(timezone.utc) - timedelta(days=90)
    record = json.loads(cache_file.read_text(encoding="utf-8"))
    record["cached_at"] = old.isoformat()
    cache_file.write_text(json.dumps(record), encoding="utf-8")

    assert get_cached_provider_response("SEC", "https://data.sec.gov/submissions/CIK1.json", None, ttl_seconds=1, settings=settings) is None


def test_file_archive_writes_split_run_artifacts(tmp_path) -> None:
    settings = Settings(file_storage_dir=str(tmp_path), file_storage_enabled=True)
    report = ResearchReport(ticker="MSFT", company_name="Microsoft", reported_facts=["Revenue reported."])
    run_dir = persist_research_run_files(
        ticker="msft",
        question="Analyze Microsoft.",
        state={
            "messages": [HumanMessage(content="Ticker: MSFT")],
            "tool_results": [{"name": "get_company_facts", "content": {"revenue": 100}}],
            "verification_passed": True,
        },
        report=report,
        external_responses=[
            {
                "provider": "SEC",
                "url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json",
                "params": {},
                "payload": {"facts": {"revenue": 100}},
            }
        ],
        job_id="job-1",
        settings=settings,
    )

    assert run_dir is not None
    assert (run_dir / "report.json").exists()
    assert (run_dir / "tool_results.json").exists()
    assert (run_dir / "provider_responses_index.json").exists()
    assert len(list((run_dir / "provider_responses").glob("*.json"))) == 1
