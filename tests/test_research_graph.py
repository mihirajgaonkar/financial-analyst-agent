from langchain_core.messages import AIMessage, ToolMessage

from financial_research.graph.research_graph import (
    create_research_agent_node,
    create_research_graph,
    should_continue,
    understand_question,
    verification_node,
)
from financial_research.graph.verification import verify_final_message


class FinalAnswerModel:
    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return AIMessage(content="Reported revenue was 100 and calculated growth was 0.2.")


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
    assert should_continue({"messages": [message], "iterations": 6}) == "verification"


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
