from langchain_core.messages import AIMessage, ToolMessage

from financial_research.graph.research_graph import (
    MAX_TOOL_ITERATIONS,
    create_final_synthesis_node,
    create_research_agent_node,
    create_research_graph,
    should_continue,
    understand_question,
    verification_node,
)
from financial_research.graph.verification import verify_final_message
from financial_research.graph.verification import build_report, extract_calculated_metrics


class FinalAnswerModel:
    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return AIMessage(content="Reported revenue was 100 and calculated growth was 0.2.")


class ToolCallThenFinalModel:
    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        if "Write the final research response now" in messages[-1].content:
            return AIMessage(content="Reported revenue was 100 based on tool results.")
        return AIMessage(
            content="",
            tool_calls=[{"name": "fake_tool", "args": {}, "id": "call-1"}],
        )


def test_understand_question_normalizes_input() -> None:
    result = understand_question({"ticker": " msft ", "research_question": " Analyze margins. "})
    assert result["ticker"] == "MSFT"
    assert result["research_question"] == "Analyze margins."
    assert result["messages"][0].content == "Ticker: MSFT\nQuestion: Analyze margins."


def test_should_continue_routes_to_tools_when_tool_calls_present() -> None:
    message = AIMessage(
        content="",
        tool_calls=[{"name": "calculate_revenue_growth", "args": {"current_revenue": 120, "prior_revenue": 100}, "id": "1"}],
    )
    assert should_continue({"messages": [message], "iterations": 1}) == "tools"


def test_should_continue_routes_to_verification_when_bounded() -> None:
    message = AIMessage(
        content="",
        tool_calls=[{"name": "calculate_revenue_growth", "args": {"current_revenue": 120, "prior_revenue": 100}, "id": "1"}],
    )
    assert should_continue({"messages": [message], "iterations": MAX_TOOL_ITERATIONS}) == "final_synthesis"


def test_should_continue_routes_to_final_synthesis_after_plain_agent_answer() -> None:
    assert should_continue({"messages": [AIMessage(content="hello")], "iterations": 1}) == "final_synthesis"


def test_verifier_flags_numbers_not_in_tool_results() -> None:
    messages = [
        ToolMessage(content='{"revenue": 100}', tool_call_id="1", name="get_company_facts"),
        AIMessage(content="Revenue was 100 and margin was 35."),
    ]
    passed, unsupported = verify_final_message(messages, [{"name": "get_company_facts", "content": {"revenue": 100}}])
    assert not passed
    assert "35" in unsupported[0]


def test_verification_node_collects_sources_and_calculated_metrics() -> None:
    state = {
        "messages": [
            ToolMessage(
                content='{"url": "https://www.sec.gov/Archives/edgar/data/1/filing.htm", "form": "10-K"}',
                tool_call_id="1",
                name="get_latest_10k",
            ),
            ToolMessage(content='{"revenue_growth": 0.2}', tool_call_id="2", name="calculate_revenue_growth"),
            AIMessage(content="SEC filing showed 10-K and calculated growth was 0.2."),
        ]
    }
    result = verification_node(state)
    assert result["verification_passed"]
    assert result["sources"][0].url == "https://www.sec.gov/Archives/edgar/data/1/filing.htm"
    assert result["calculated_metrics"][0].name == "revenue_growth"


def test_graph_runs_to_final_report_without_tool_calls() -> None:
    graph = create_research_graph(llm=FinalAnswerModel(), tools=[])
    result = graph.invoke({"ticker": "MSFT", "research_question": "Summarize."})
    assert result["final_report"].ticker == "MSFT"
    assert not result["verification_passed"]
    assert result["unsupported_claims"]


def test_research_agent_node_invokes_bound_model() -> None:
    node = create_research_agent_node(FinalAnswerModel(), [])
    result = node({"messages": [], "iterations": 0})
    assert result["iterations"] == 1
    assert result["messages"][0].content.startswith("Reported revenue")


def test_final_synthesis_node_forces_narrative_response() -> None:
    node = create_final_synthesis_node(ToolCallThenFinalModel())
    result = node({"messages": [AIMessage(content="", tool_calls=[{"name": "fake_tool", "args": {}, "id": "call-1"}])]})
    assert result["messages"][0].content.startswith("Reported revenue")


def test_build_report_maps_tool_payloads_to_sections_and_kpis() -> None:
    report = build_report(
        {
            "ticker": "MSFT",
            "tool_results": [
                {"name": "get_company_profile", "content": {"company_name": "Microsoft Corporation"}},
                {"name": "get_stock_price", "content": {"price": 100}},
                {"name": "get_company_facts", "content": {
                    "facts": {"revenue": 125, "operating_income": 25, "eps": 5},
                    "historical_facts": {"revenue": [
                        {"value": 125, "end": "2025-09-30"}, {"value": 100, "end": "2024-09-30"}
                    ]},
                    "source_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json",
                }},
                {"name": "get_latest_10k", "content": {"form": "10-K", "url": "https://www.sec.gov/Archives/edgar/data/1/filing.htm"}},
            ],
            "calculated_metrics": extract_calculated_metrics(
                [
                    {"name": "calculate_revenue_growth", "content": {"revenue_growth": 0.178}},
                    {"name": "calculate_revenue_growth", "content": {"revenue_growth": 0.149}},
                    {"name": "calculate_margins", "content": {"gross_margin": 0.679}},
                ]
            ),
        },
        "Verified research summary.",
    )
    assert report.company_name == "Microsoft Corporation"
    assert {metric.name for metric in report.calculated_metrics} >= {"price", "revenue_growth", "operating_margin", "pe_ratio"}
    assert report.growth_analysis and report.profitability_analysis
    assert report.filings[0].title == "10-K"
    assert any("data.sec.gov" in (source.url or "") for source in report.sources)


def test_build_report_formats_growth_and_deduplicates_summary_metrics() -> None:
    tool_results = [
        {"name": "calculate_revenue_growth", "content": {"revenue_growth": 0.178}},
        {"name": "calculate_revenue_growth", "content": {"revenue_growth": 0.149}},
        {"name": "calculate_margins", "content": {"gross_margin": 0.679}},
    ]
    report = build_report(
        {
            "ticker": "MSFT",
            "tool_results": tool_results,
            "calculated_metrics": extract_calculated_metrics(tool_results),
        },
        "SEC-only research.",
    )
    assert report.growth_analysis == "Growth: 17.8% (reported period). Source: calculate_revenue_growth."
    assert [metric.name for metric in report.key_financials] == ["revenue_growth", "gross_margin"]


def test_build_report_rejects_stale_revenue_growth() -> None:
    report = build_report(
        {
            "ticker": "NVDA",
            "tool_results": [
                {
                    "name": "get_company_facts",
                    "content": {
                        "facts": {
                            "revenue": 26_914_000_000,
                            "operating_income": 130_387_000_000,
                        },
                        "historical_facts": {
                            "revenue": [
                                {"value": 26_914_000_000, "end": "2022-01-30"},
                                {"value": 16_675_000_000, "end": "2021-01-31"},
                            ],
                            "operating_income": [
                                {"value": 130_387_000_000, "end": "2026-01-25"},
                                {"value": 81_453_000_000, "end": "2025-01-26"},
                            ],
                        },
                    },
                }
            ],
            "calculated_metrics": [],
        },
        "SEC facts summary.",
    )

    assert not any(metric.name == "revenue_growth" for metric in report.calculated_metrics)
    assert report.growth_analysis == "Growth: Revenue growth could not be calculated from two annual SEC periods."
