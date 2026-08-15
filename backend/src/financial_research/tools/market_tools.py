from typing import Any

from langchain.tools import tool

from financial_research.services.exceptions import RateLimitError
from financial_research.services.market_data import MarketDataProvider, get_market_data_provider


def create_market_tools(provider: MarketDataProvider | None = None) -> list:
    market = provider or get_market_data_provider()

    @tool
    def get_stock_price(ticker: str) -> dict[str, Any]:
        """Fetch the latest stock quote for a public company ticker."""
        try:
            return {**market.get_quote(ticker).model_dump(mode="json"), "source": "Market data provider"}
        except RateLimitError as exc:
            return _rate_limited_result("get_stock_price", ticker, exc)

    @tool
    def get_price_history(ticker: str) -> list[dict[str, Any]]:
        """Fetch recent daily price history for a public company ticker."""
        try:
            return [price.model_dump(mode="json") for price in market.get_price_history(ticker)]
        except RateLimitError as exc:
            return [_rate_limited_result("get_price_history", ticker, exc)]

    @tool
    def get_company_overview(ticker: str) -> dict[str, Any]:
        """Fetch market-data provider company overview information for a ticker."""
        try:
            return {**market.get_company_overview(ticker).model_dump(mode="json"), "source": "Market data provider"}
        except RateLimitError as exc:
            return _rate_limited_result("get_company_overview", ticker, exc)

    return [get_stock_price, get_price_history, get_company_overview]


def _rate_limited_result(tool_name: str, ticker: str, error: RateLimitError) -> dict[str, Any]:
    return {
        "ticker": ticker.upper(),
        "available": False,
        "source": "Alpha Vantage",
        "error_type": "rate_limit",
        "tool": tool_name,
        "message": str(error),
    }
