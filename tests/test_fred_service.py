import httpx
import pytest

from financial_research.config.settings import Settings
from financial_research.services.exceptions import ExternalServiceError
from financial_research.services.fred import FREDService, parse_fred_observations


def test_fred_parsing_skips_missing_values() -> None:
    indicators = parse_fred_observations(
        "DGS10",
        "10-Year Treasury Yield",
        {"observations": [{"date": "2026-08-07", "value": "4.25"}, {"date": "2026-08-06", "value": "."}]},
    )
    assert len(indicators) == 1
    assert indicators[0].value == pytest.approx(4.25)


def test_fred_http_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    service = FREDService(settings=Settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ExternalServiceError):
        service.get_fred_series("FEDFUNDS")
