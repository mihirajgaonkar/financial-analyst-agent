import argparse
import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from financial_research.services.exceptions import FinancialResearchError
from financial_research.services.fred import FREDService
from financial_research.services.sec import SECService, parse_company_facts_metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Financial Research Agent Phase 1 CLI")
    parser.add_argument("--company", help="Ticker symbol to fetch SEC data for.")
    parser.add_argument("--macro", action="store_true", help="Fetch default FRED macro indicators.")
    args = parser.parse_args()

    try:
        if args.company:
            sec = SECService()
            cik = sec.get_company_cik(args.company)
            facts = sec.get_company_facts(cik)
            latest_10k = sec.get_latest_10k(cik)
            latest_10q = sec.get_latest_10q(cik)
            output = {
                "ticker": args.company.upper(),
                "cik": cik,
                "latest_10k": latest_10k,
                "latest_10q": latest_10q,
                "facts_snapshot": parse_company_facts_metrics(args.company, facts),
            }
            print(_to_json(output))
            return 0

        if args.macro:
            fred = FREDService()
            print(_to_json(fred.get_default_indicators()))
            return 0

        parser.print_help()
        return 1
    except FinancialResearchError as exc:
        print(f"Error: {exc}")
        return 2


def _to_json(value: Any) -> str:
    return json.dumps(_jsonable(value), indent=2)


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
