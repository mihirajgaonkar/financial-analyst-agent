import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from financial_research.debug.recorder import capture_external_responses, record_external_response
from financial_research.debug.report_writer import write_debug_report
from financial_research.schemas.reports import ResearchReport


def test_external_response_recorder_captures_and_redacts_parameters() -> None:
    with capture_external_responses() as responses:
        record_external_response(
            "FRED",
            "https://api.stlouisfed.org/fred/series/observations",
            {"series_id": "FEDFUNDS", "api_key": "secret-value"},
            {"observations": [{"value": "3.63"}]},
        )

    assert responses[0]["params"]["api_key"] == "<redacted>"
    assert responses[0]["payload"]["observations"][0]["value"] == "3.63"


def test_debug_report_writes_markdown_and_raw_json(tmp_path) -> None:
    report = ResearchReport(ticker="AAPL", company_name="Apple", executive_summary="Macro summary.")
    state = {
        "iterations": 1,
        "messages": [
            HumanMessage(content="Ticker: AAPL\nQuestion: Get interest rates."),
            AIMessage(content="", tool_calls=[{"name": "get_interest_rates", "args": {}, "id": "1"}]),
            ToolMessage(
                content='{"FEDFUNDS": [{"value": 3.63, "date": "2026-07-01"}]}',
                name="get_interest_rates",
                tool_call_id="1",
            ),
            AIMessage(content="Rates may affect valuation."),
        ],
        "tool_results": [{"name": "get_interest_rates", "content": {"FEDFUNDS": [{"value": 3.63}]}}],
        "verification_passed": True,
        "unsupported_claims": [],
        "final_report": report,
    }

    path = write_debug_report(
        state,
        ticker="AAPL",
        question="Get interest rates.",
        output_dir=str(tmp_path),
        system_prompt="Never invent financial data.",
        external_responses=[
            {
                "provider": "FRED",
                "url": "https://api.stlouisfed.org/fred/series/observations",
                "params": {"api_key": "<redacted>"},
                "payload": {"observations": [{"value": "3.63"}]},
            }
        ],
    )

    raw_path = path.with_suffix(".raw.json")
    assert path.exists()
    assert raw_path.exists()
    markdown = path.read_text(encoding="utf-8")
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    assert "get_interest_rates" in markdown
    assert "Never invent financial data." in markdown
    assert raw[0]["payload"]["observations"][0]["value"] == "3.63"
    assert "secret-value" not in markdown
    assert "secret-value" not in raw_path.read_text(encoding="utf-8")
