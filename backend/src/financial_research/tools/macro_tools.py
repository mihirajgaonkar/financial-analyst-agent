from typing import Any

from langchain.tools import tool

from financial_research.services.fred import DEFAULT_INDICATORS, FREDService


def create_macro_tools(fred_service: FREDService | None = None) -> list:
    service = fred_service or FREDService()

    @tool
    def get_macro_indicator(series_id: str) -> list[dict[str, Any]]:
        """Fetch the latest FRED observation for a macroeconomic series ID."""
        return [indicator.model_dump(mode="json") for indicator in service.get_fred_series(series_id, limit=1)]

    @tool
    def get_interest_rates() -> dict[str, list[dict[str, Any]]]:
        """Fetch core interest-rate indicators from FRED."""
        return {
            series_id: [indicator.model_dump(mode="json") for indicator in service.get_fred_series(series_id, limit=1)]
            for series_id in ("FEDFUNDS", "DGS10")
        }

    @tool
    def get_default_macro_indicators() -> dict[str, list[dict[str, Any]]]:
        """Fetch the default Phase 1 macro indicators from FRED."""
        return {
            series_id: [indicator.model_dump(mode="json") for indicator in service.get_fred_series(series_id, limit=1)]
            for series_id in DEFAULT_INDICATORS
        }

    return [get_macro_indicator, get_interest_rates, get_default_macro_indicators]
