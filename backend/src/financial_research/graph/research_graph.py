from typing import Any, Literal, Sequence

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from financial_research.agents.research_agent import RESEARCH_SYSTEM_PROMPT
from financial_research.graph.state import ResearchGraphState
from financial_research.graph.verification import (
    collect_tool_results,
    extract_calculated_metrics,
    extract_sources,
    verify_final_message,
)
from financial_research.llm.model import get_llm
from financial_research.schemas.reports import ResearchReport
from financial_research.tools import create_research_tools

MAX_TOOL_ITERATIONS = 3


def understand_question(state: ResearchGraphState) -> dict[str, Any]:
    ticker = state.get("ticker", "").upper().strip()
    question = state.get("research_question", "").strip()
    if not ticker:
        raise ValueError("ticker is required.")
    if not question:
        raise ValueError("research_question is required.")
    return {
        "ticker": ticker,
        "research_question": question,
        "iterations": 0,
        "messages": [HumanMessage(content=f"Ticker: {ticker}\nQuestion: {question}")],
    }


def create_research_agent_node(llm: Any, tools: Sequence[Any]):
    model = llm.bind_tools(list(tools)) if hasattr(llm, "bind_tools") else llm

    def research_agent(state: ResearchGraphState) -> dict[str, Any]:
        messages = [SystemMessage(content=RESEARCH_SYSTEM_PROMPT), *state.get("messages", [])]
        response = model.invoke(messages)
        return {"messages": [response], "iterations": state.get("iterations", 0) + 1}

    return research_agent


def should_continue(state: ResearchGraphState) -> Literal["tools", "verification"]:
    messages = state.get("messages", [])
    if state.get("iterations", 0) >= MAX_TOOL_ITERATIONS:
        return "verification"
    if messages and getattr(messages[-1], "tool_calls", None):
        return "tools"
    return "verification"


def verification_node(state: ResearchGraphState) -> dict[str, Any]:
    tool_results = collect_tool_results(state.get("messages", []))
    sources = extract_sources(tool_results)
    calculated_metrics = extract_calculated_metrics(tool_results)
    verification_passed, unsupported_claims = verify_final_message(state.get("messages", []), tool_results)
    return {
        "tool_results": tool_results,
        "sources": sources,
        "calculated_metrics": calculated_metrics,
        "verification_passed": verification_passed,
        "unsupported_claims": unsupported_claims,
    }


def report_node(state: ResearchGraphState) -> dict[str, Any]:
    final_text = _last_ai_message_text(state.get("messages", []))
    report = ResearchReport(
        ticker=state["ticker"],
        company_name=state.get("ticker", ""),
        executive_summary=final_text,
        reported_facts=[],
        calculated_metrics=state.get("calculated_metrics", []),
        key_financials=state.get("calculated_metrics", []),
        llm_interpretation=final_text,
        sources=state.get("sources", []),
    )
    return {"final_report": report}


def create_research_graph(llm: Any | None = None, tools: Sequence[Any] | None = None):
    selected_tools = list(tools or create_research_tools())
    model = llm or get_llm()

    builder = StateGraph(ResearchGraphState)
    builder.add_node("understand_question", understand_question)
    builder.add_node("research_agent", create_research_agent_node(model, selected_tools))
    builder.add_node("tools", ToolNode(selected_tools))
    builder.add_node("verification", verification_node)
    builder.add_node("report", report_node)

    builder.add_edge(START, "understand_question")
    builder.add_edge("understand_question", "research_agent")
    builder.add_conditional_edges(
        "research_agent",
        should_continue,
        {"tools": "tools", "verification": "verification"},
    )
    builder.add_edge("tools", "research_agent")
    builder.add_edge("verification", "report")
    builder.add_edge("report", END)

    return builder.compile()


def run_research_graph(ticker: str, research_question: str, llm: Any | None = None) -> ResearchGraphState:
    graph = create_research_graph(llm=llm)
    return graph.invoke({"ticker": ticker, "research_question": research_question}, {"recursion_limit": 16})


def _last_ai_message_text(messages: list[Any]) -> str:
    for message in reversed(messages):
        if getattr(message, "type", None) == "ai":
            content = message.content
            return content if isinstance(content, str) else str(content)
    return ""
