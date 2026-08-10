from financial_research.agents.research_agent import RESEARCH_SYSTEM_PROMPT, create_structured_report_llm
from financial_research.schemas.reports import ResearchReport


class FakeStructuredLLM:
    def __init__(self) -> None:
        self.schema = None

    def with_structured_output(self, schema):
        self.schema = schema
        return self


def test_research_prompt_contains_financial_safety_rules() -> None:
    assert "Never invent financial data" in RESEARCH_SYSTEM_PROMPT
    assert "deterministic calculation tools" in RESEARCH_SYSTEM_PROMPT
    assert "traceable to a source" in RESEARCH_SYSTEM_PROMPT


def test_structured_report_llm_uses_research_report_schema() -> None:
    llm = FakeStructuredLLM()
    assert create_structured_report_llm(llm) is llm
    assert llm.schema is ResearchReport
