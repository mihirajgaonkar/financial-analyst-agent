from operator import add
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from financial_research.schemas.financials import FinancialMetric
from financial_research.schemas.reports import ResearchReport, ResearchSource


class ResearchGraphState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    ticker: str
    research_question: str
    sources: Annotated[list[ResearchSource], add]
    calculated_metrics: Annotated[list[FinancialMetric], add]
    tool_results: Annotated[list[dict[str, Any]], add]
    unsupported_claims: Annotated[list[str], add]
    verification_passed: bool
    final_report: ResearchReport | None
    iterations: int
