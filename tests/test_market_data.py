import httpx
import pytest

from financial_research.config.settings import Settings
from financial_research.services.exceptions import ExternalServiceError, InvalidTickerError
from financial_research.services.market_data import (
    AlphaVantageProvider,
    parse_alpha_vantage_history,
    parse_alpha_vantage_quote,
)


def test_alpha_vantage_quote_parsing() -> None:
    quote = parse_alpha_vantage_quote(
        "msft",
        {"Global Quote": {"05. price": "420.50", "02. open": "419", "03. high": "422", "04. low": "418", "06. volume": "12345"}},
    )
    assert quote.ticker == "MSFT"
    assert quote.price == pytest.approx(420.50)
    assert quote.volume == 12345


def test_alpha_vantage_history_parsing() -> None:
    history = parse_alpha_vantage_history(
        "MSFT",
        {"Time Series (Daily)": {"2026-08-07": {"1. open": "10", "2. high": "12", "3. low": "9", "4. close": "11", "6. volume": "100"}}},
    )
    assert history[0].price == pytest.approx(11)


def test_alpha_vantage_invalid_ticker() -> None:
    with pytest.raises(InvalidTickerError):
        parse_alpha_vantage_quote("BAD", {"Global Quote": {}})


def test_alpha_vantage_provider_failure_note() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Note": "rate limit"})

    provider = AlphaVantageProvider(settings=Settings(alpha_vantage_api_key="demo"), client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ExternalServiceError):
        provider.get_quote("MSFT")
