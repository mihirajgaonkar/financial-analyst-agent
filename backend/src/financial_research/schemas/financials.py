from datetime import date, datetime

from pydantic import BaseModel, Field


class PriceData(BaseModel):
    ticker: str
    price: float
    currency: str = "USD"
    as_of: datetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: int | None = None


class FinancialStatementMetrics(BaseModel):
    ticker: str
    fiscal_period: str
    fiscal_year: int | None = None
    period_end: date | None = None
    revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    operating_cash_flow: float | None = None
    capital_expenditures: float | None = None
    total_debt: float | None = None
    total_equity: float | None = None
    ebitda: float | None = None
    enterprise_value: float | None = None


class FinancialMetric(BaseModel):
    name: str
    value: float
    unit: str | None = None
    period: str | None = None
    source: str | None = None
    calculated: bool = True
    inputs: dict[str, float] = Field(default_factory=dict)
