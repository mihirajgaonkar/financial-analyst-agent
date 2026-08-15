from datetime import datetime
from typing import Any

import httpx

from financial_research.config.settings import Settings, get_settings
from financial_research.debug.recorder import record_external_response
from financial_research.schemas.reports import MacroIndicator
from financial_research.services.exceptions import ExternalServiceError

FRED_BASE_URL = "https://api.stlouisfed.org/fred"
DEFAULT_INDICATORS = {
    "FEDFUNDS": "Federal Funds Rate",
    "DGS10": "10-Year Treasury Yield",
    "CPIAUCSL": "Consumer Price Index",
    "UNRATE": "Unemployment Rate",
    "GDP": "Gross Domestic Product",
}


class FREDService:
    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client or httpx.Client(timeout=20)

    def get_fred_series(
        self,
        series_id: str,
        observation_start: str | None = None,
        limit: int = 1,
    ) -> list[MacroIndicator]:
        params: dict[str, Any] = {
            "series_id": series_id,
            "api_key": self.settings.fred_api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }
        if observation_start:
            params["observation_start"] = observation_start
        data = self._get_json(f"{FRED_BASE_URL}/series/observations", params=params)
        return parse_fred_observations(series_id, DEFAULT_INDICATORS.get(series_id, series_id), data)

    def get_default_indicators(self) -> list[MacroIndicator]:
        indicators: list[MacroIndicator] = []
        for series_id in DEFAULT_INDICATORS:
            indicators.extend(self.get_fred_series(series_id, limit=1))
        return indicators

    def _get_json(self, url: str, params: dict[str, Any]) -> Any:
        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            record_external_response("FRED", url, params, payload)
            return payload
        except httpx.HTTPStatusError as exc:
            raise ExternalServiceError(f"FRED request failed with status {exc.response.status_code}: {url}") from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"FRED request failed: {url}") from exc


def parse_fred_observations(series_id: str, name: str, payload: dict[str, Any]) -> list[MacroIndicator]:
    indicators: list[MacroIndicator] = []
    for observation in payload.get("observations", []):
        value = observation.get("value")
        if value in (None, "."):
            continue
        indicators.append(
            MacroIndicator(
                series_id=series_id,
                name=name,
                value=float(value),
                date=datetime.strptime(observation["date"], "%Y-%m-%d").date(),
            )
        )
    return indicators
