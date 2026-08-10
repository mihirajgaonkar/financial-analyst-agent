from pydantic import BaseModel, Field


class CompanyInfo(BaseModel):
    ticker: str = Field(min_length=1)
    name: str
    cik: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    description: str | None = None
    market_cap: float | None = None
