from collections.abc import Sequence
from typing import Any

from financial_research.llm.model import get_llm
from financial_research.schemas.reports import ResearchReport
from financial_research.tools import create_research_tools

RESEARCH_SYSTEM_PROMPT = """You are a financial research supervisor agent.

Rules:
- Never invent financial data.
- Use tools for factual financial information.
- Use deterministic calculation tools for arithmetic and ratios.
- Every important factual conclusion must be traceable to a source.
- Always identify the time period associated with financial figures.
- Distinguish reported facts, calculated metrics, and model interpretation.
- If information cannot be verified, say so.
- This is research support, not guaranteed investment advice.
"""


def create_research_agent(llm: Any | None = None, tools: Sequence[Any] | None = None):
    """Create the Phase 2 single tool-calling research agent."""
    from langchain.agents import create_agent

    model = llm or get_llm()
    return create_agent(
        model=model,
        tools=list(tools or create_research_tools()),
        system_prompt=RESEARCH_SYSTEM_PROMPT,
    )


def create_structured_report_llm(llm: Any | None = None):
    """Return an LLM configured to produce the ResearchReport schema."""
    model = llm or get_llm()
    if not hasattr(model, "with_structured_output"):
        raise TypeError("Configured LLM does not support structured output.")
    return model.with_structured_output(ResearchReport)


def analyze_company(ticker: str, question: str, llm: Any | None = None) -> Any:
    """Run the Phase 2 agent for a company research question."""
    agent = create_research_agent(llm=llm)
    return agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Ticker: {ticker.upper()}\nQuestion: {question}",
                }
            ]
        }
    )
