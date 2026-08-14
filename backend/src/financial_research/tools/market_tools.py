from typing import Any

from langchain.tools import tool

from financial_research.services.market_data import MarketDataProvider, get_market_data_provider


def create_market_tools(provider: MarketDataProvider | None = None) -> list:
    market = provider or get_market_data_provider()

    @tool
    def get_stock_price(ticker: str) -> dict[str, Any]:
        """Fetch the latest stock quote for a public company ticker."""
        return {**market.get_quote(ticker).model_dump(mode="json"), "source": "Market data provider"}

    @tool
    def get_price_history(ticker: str) -> list[dict[str, Any]]:
        """Fetch recent daily price history for a public company ticker."""
        return [price.model_dump(mode="json") for price in market.get_price_history(ticker)]

    @tool
    def get_company_overview(ticker: str) -> dict[str, Any]:
        """Fetch market-data provider company overview information for a ticker."""
        return {**market.get_company_overview(ticker).model_dump(mode="json"), "source": "Market data provider"}

    return [get_stock_price, get_price_history, get_company_overview]
