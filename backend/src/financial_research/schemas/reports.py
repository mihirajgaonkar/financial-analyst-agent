from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from financial_research.schemas.financials import FinancialMetric


class MacroIndicator(BaseModel):
    series_id: str
    name: str
    value: float
    date: date
    units: str | None = None
    source: str = "FRED"


class ResearchSource(BaseModel):
    source_type: str
    title: str
    url: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchReport(BaseModel):
    ticker: str
    company_name: str
    executive_summary: str | None = None
    reported_facts: list[str] = Field(default_factory=list)
    calculated_metrics: list[FinancialMetric] = Field(default_factory=list)
    key_financials: list[FinancialMetric] = Field(default_factory=list)
    growth_analysis: str | None = None
    profitability_analysis: str | None = None
    valuation_analysis: str | None = None
    macro_indicators: list[MacroIndicator] = Field(default_factory=list)
    filings: list[ResearchSource] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    llm_interpretation: str | None = None
    sources: list[ResearchSource] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    report_type: Literal["phase_1_raw", "research"] = "research"
