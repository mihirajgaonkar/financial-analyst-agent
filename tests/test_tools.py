from datetime import date, datetime, timezone

from financial_research.schemas.company import CompanyInfo
from financial_research.schemas.filings import SECFiling
from financial_research.schemas.financials import PriceData
from financial_research.schemas.reports import MacroIndicator
from financial_research.tools.calculation_tools import calculate_revenue_growth
from financial_research.tools.macro_tools import create_macro_tools
from financial_research.tools.market_tools import create_market_tools
from financial_research.tools.sec_tools import create_sec_tools


class FakeSECService:
    def get_company_cik(self, ticker: str) -> str:
        return "0000789019"

    def get_company_submissions(self, cik: str) -> dict:
        return {"name": "Microsoft Corporation", "sic": "7372", "sicDescription": "Services-Prepackaged Software"}

    def get_company_facts(self, cik: str) -> dict:
        return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [{"end": "2025-06-30", "val": 100}]}}}}}

    def get_latest_10k(self, cik: str) -> SECFiling:
        return SECFiling(cik=cik, accession_number="1", form="10-K", filing_date=date(2025, 7, 30))

    def get_latest_10q(self, cik: str) -> SECFiling:
        return SECFiling(cik=cik, accession_number="2", form="10-Q", filing_date=date(2026, 1, 30))


class FakeMarketProvider:
    def get_quote(self, ticker: str) -> PriceData:
        return PriceData(ticker=ticker, price=100, as_of=datetime.now(timezone.utc))

    def get_price_history(self, ticker: str) -> list[PriceData]:
        return [self.get_quote(ticker)]

    def get_company_overview(self, ticker: str) -> CompanyInfo:
        return CompanyInfo(ticker=ticker, name="Microsoft Corporation", market_cap=300)


class FakeFREDService:
    def get_fred_series(self, series_id: str, observation_start: str | None = None, limit: int = 1) -> list[MacroIndicator]:
        return [MacroIndicator(series_id=series_id, name=series_id, value=4.5, date=date(2026, 8, 7))]


def test_sec_tools_delegate_to_service() -> None:
    tools = {tool.name: tool for tool in create_sec_tools(FakeSECService())}
    profile = tools["get_company_profile"].invoke({"ticker": "MSFT"})
    facts = tools["get_company_facts"].invoke({"ticker": "MSFT"})
    assert profile["cik"] == "0000789019"
    assert facts["facts"]["revenue"] == 100


def test_market_tools_delegate_to_provider() -> None:
    tools = {tool.name: tool for tool in create_market_tools(FakeMarketProvider())}
    quote = tools["get_stock_price"].invoke({"ticker": "MSFT"})
    overview = tools["get_company_overview"].invoke({"ticker": "MSFT"})
    assert quote["price"] == 100
    assert overview["market_cap"] == 300


def test_macro_tools_delegate_to_service() -> None:
    tools = {tool.name: tool for tool in create_macro_tools(FakeFREDService())}
    rates = tools["get_interest_rates"].invoke({})
    assert rates["FEDFUNDS"][0]["value"] == 4.5
    assert rates["DGS10"][0]["source"] == "FRED"


def test_calculation_tool_uses_deterministic_function() -> None:
    result = calculate_revenue_growth.invoke({"current_revenue": 120, "prior_revenue": 100})
    assert result["revenue_growth"] == 0.2
