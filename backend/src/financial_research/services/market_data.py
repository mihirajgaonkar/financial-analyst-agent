from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

from financial_research.config.settings import Settings, get_settings
from financial_research.debug.recorder import record_external_response
from financial_research.schemas.company import CompanyInfo
from financial_research.schemas.financials import PriceData
from financial_research.services.exceptions import ExternalServiceError, InvalidTickerError, RateLimitError


class MarketDataProvider(Protocol):
    def get_quote(self, ticker: str) -> PriceData: ...

    def get_price_history(self, ticker: str) -> list[PriceData]: ...

    def get_company_overview(self, ticker: str) -> CompanyInfo: ...


class AlphaVantageProvider:
    base_url = "https://www.alphavantage.co/query"

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client or httpx.Client(timeout=20)

    def get_quote(self, ticker: str) -> PriceData:
        payload = self._request({"function": "GLOBAL_QUOTE", "symbol": ticker})
        return parse_alpha_vantage_quote(ticker, payload)

    def get_price_history(self, ticker: str) -> list[PriceData]:
        payload = self._request({"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": ticker, "outputsize": "compact"})
        return parse_alpha_vantage_history(ticker, payload)

    def get_company_overview(self, ticker: str) -> CompanyInfo:
        payload = self._request({"function": "OVERVIEW", "symbol": ticker})
        if not payload or "Symbol" not in payload:
            raise InvalidTickerError(f"Market data provider did not return a company overview for {ticker}.")
        return CompanyInfo(
            ticker=payload["Symbol"],
            name=payload.get("Name", ""),
            exchange=payload.get("Exchange") or None,
            sector=payload.get("Sector") or None,
            industry=payload.get("Industry") or None,
            description=payload.get("Description") or None,
            market_cap=_to_float(payload.get("MarketCapitalization")),
        )

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "apikey": self.settings.alpha_vantage_api_key}
        try:
            response = self.client.get(self.base_url, params=params)
            response.raise_for_status()
            payload = response.json()
            record_external_response("Alpha Vantage", self.base_url, params, payload)
        except httpx.HTTPStatusError as exc:
            raise ExternalServiceError(f"Market data request failed with status {exc.response.status_code}.") from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Market data request failed.") from exc
        if "Error Message" in payload:
            raise InvalidTickerError(payload["Error Message"])
        if "Note" in payload or "Information" in payload:
            message = payload.get("Note") or payload.get("Information") or "Market data provider rate limit reached."
            if _is_rate_limit_message(message):
                raise RateLimitError(_rate_limit_message(message))
            raise ExternalServiceError(message)
        return payload


def get_market_data_provider(settings: Settings | None = None) -> MarketDataProvider:
    settings = settings or get_settings()
    if settings.market_data_provider.lower() == "alpha_vantage":
        return AlphaVantageProvider(settings=settings)
    raise ValueError(f"Unsupported MARKET_DATA_PROVIDER: {settings.market_data_provider}")


def parse_alpha_vantage_quote(ticker: str, payload: dict[str, Any]) -> PriceData:
    quote = payload.get("Global Quote", {})
    price = _to_float(quote.get("05. price"))
    if price is None:
        raise InvalidTickerError(f"No quote found for ticker: {ticker}")
    return PriceData(
        ticker=ticker.upper(),
        price=price,
        as_of=datetime.now(timezone.utc),
        open=_to_float(quote.get("02. open")),
        high=_to_float(quote.get("03. high")),
        low=_to_float(quote.get("04. low")),
        volume=int(float(quote["06. volume"])) if quote.get("06. volume") else None,
    )


def parse_alpha_vantage_history(ticker: str, payload: dict[str, Any]) -> list[PriceData]:
    series = payload.get("Time Series (Daily)", {})
    prices: list[PriceData] = []
    for date_text, values in series.items():
        prices.append(
            PriceData(
                ticker=ticker.upper(),
                price=float(values["4. close"]),
                as_of=datetime.fromisoformat(date_text).replace(tzinfo=timezone.utc),
                open=_to_float(values.get("1. open")),
                high=_to_float(values.get("2. high")),
                low=_to_float(values.get("3. low")),
                volume=int(float(values["6. volume"])) if values.get("6. volume") else None,
            )
        )
    if not prices:
        raise InvalidTickerError(f"No price history found for ticker: {ticker}")
    return sorted(prices, key=lambda price: price.as_of)


def _to_float(value: Any) -> float | None:
    if value in (None, "", "None"):
        return None
    return float(value)


def _is_rate_limit_message(message: str) -> bool:
    lowered = message.lower()
    return "rate limit" in lowered or "free api requests" in lowered or "requests per day" in lowered or "requests per second" in lowered


def _rate_limit_message(message: str) -> str:
    if "25 requests per day" in message:
        return (
            "Alpha Vantage free-tier limit reached. The provider allows 25 requests per day and asks requests to be "
            "spread out to about 1 request per second. Wait for the quota window to reset, slow request volume, or use "
            "a premium key."
        )
    return f"Alpha Vantage rate limit reached: {message}"
