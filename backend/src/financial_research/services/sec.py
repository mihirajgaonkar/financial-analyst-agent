from datetime import datetime
from typing import Any

import httpx

from financial_research.config.settings import Settings, get_settings
from financial_research.schemas.filings import SECFiling
from financial_research.services.exceptions import ExternalServiceError, InvalidTickerError

SEC_DATA_BASE = "https://data.sec.gov"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


class SECService:
    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client or httpx.Client(timeout=20)

    @property
    def headers(self) -> dict[str, str]:
        return {"User-Agent": self.settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"}

    def get_company_cik(self, ticker: str) -> str:
        ticker = ticker.upper().strip()
        if not ticker:
            raise InvalidTickerError("Ticker cannot be empty.")
        data = self._get_json(SEC_TICKERS_URL)
        for company in data.values():
            if company.get("ticker", "").upper() == ticker:
                return str(company["cik_str"]).zfill(10)
        raise InvalidTickerError(f"Ticker not found in SEC company tickers: {ticker}")

    def get_company_submissions(self, cik: str) -> dict[str, Any]:
        cik = cik.zfill(10)
        return self._get_json(f"{SEC_DATA_BASE}/submissions/CIK{cik}.json")

    def get_company_facts(self, cik: str) -> dict[str, Any]:
        cik = cik.zfill(10)
        return self._get_json(f"{SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{cik}.json")

    def get_recent_filings(self, cik: str) -> list[SECFiling]:
        submissions = self.get_company_submissions(cik)
        recent = submissions.get("filings", {}).get("recent", {})
        return parse_recent_filings(cik.zfill(10), recent)

    def get_latest_10k(self, cik: str) -> SECFiling | None:
        return self._latest_by_form(cik, "10-K")

    def get_latest_10q(self, cik: str) -> SECFiling | None:
        return self._latest_by_form(cik, "10-Q")

    def _latest_by_form(self, cik: str, form: str) -> SECFiling | None:
        filings = [filing for filing in self.get_recent_filings(cik) if filing.form == form]
        return max(filings, key=lambda filing: filing.filing_date, default=None)

    def _get_json(self, url: str) -> Any:
        try:
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise ExternalServiceError(f"SEC request failed with status {exc.response.status_code}: {url}") from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"SEC request failed: {url}") from exc


def parse_recent_filings(cik: str, recent: dict[str, list[Any]]) -> list[SECFiling]:
    forms = recent.get("form", [])
    filings: list[SECFiling] = []
    for index, form in enumerate(forms):
        accession = recent["accessionNumber"][index]
        primary_document = _optional_at(recent, "primaryDocument", index)
        filings.append(
            SECFiling(
                cik=cik.zfill(10),
                accession_number=accession,
                form=form,
                filing_date=datetime.strptime(recent["filingDate"][index], "%Y-%m-%d").date(),
                report_date=_parse_optional_date(_optional_at(recent, "reportDate", index)),
                primary_document=primary_document,
                url=build_filing_url(cik, accession, primary_document),
            )
        )
    return filings


def parse_company_facts_metrics(ticker: str, facts: dict[str, Any]) -> dict[str, float]:
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    concepts = {
        "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
        "net_income": ["NetIncomeLoss"],
        "assets": ["Assets"],
        "liabilities": ["Liabilities"],
        "equity": ["StockholdersEquity"],
    }
    parsed: dict[str, float] = {}
    for output_name, concept_names in concepts.items():
        for concept_name in concept_names:
            concept = us_gaap.get(concept_name)
            if not concept:
                continue
            unit_values = concept.get("units", {}).get("USD", [])
            latest = _latest_numeric_fact(unit_values)
            if latest is not None:
                parsed[output_name] = latest
                break
    return parsed


def build_filing_url(cik: str, accession_number: str, primary_document: str | None) -> str | None:
    if not primary_document:
        return None
    cik_int = str(int(cik))
    accession_no_dashes = accession_number.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_no_dashes}/{primary_document}"


def _latest_numeric_fact(values: list[dict[str, Any]]) -> float | None:
    candidates = [value for value in values if "val" in value and value.get("end")]
    if not candidates:
        return None
    latest = max(candidates, key=lambda value: value["end"])
    return float(latest["val"])


def _optional_at(data: dict[str, list[Any]], key: str, index: int) -> Any | None:
    values = data.get(key, [])
    return values[index] if index < len(values) else None


def _parse_optional_date(value: str | None):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()
