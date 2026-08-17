from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from financial_research.config.settings import Settings, get_settings
from financial_research.schemas.reports import ResearchReport


def persist_research_run_files(
    *,
    ticker: str,
    question: str,
    state: dict[str, Any],
    report: ResearchReport,
    external_responses: list[dict[str, Any]],
    job_id: str | None = None,
    settings: Settings | None = None,
) -> Path | None:
    settings = settings or get_settings()
    if not settings.file_storage_enabled:
        return None

    run_dir = _run_dir(settings.file_storage_dir, ticker, job_id)
    provider_dir = run_dir / "provider_responses"
    provider_dir.mkdir(parents=True, exist_ok=True)

    _write_json(run_dir / "metadata.json", _metadata(ticker, question, state, job_id))
    _write_json(run_dir / "report.json", report)
    _write_json(run_dir / "graph_trace.json", {key: value for key, value in state.items() if key != "messages"})
    _write_json(run_dir / "messages.json", state.get("messages", []))
    _write_json(run_dir / "tool_results.json", state.get("tool_results", []))

    index: list[dict[str, Any]] = []
    for position, response in enumerate(external_responses, start=1):
        filename = _provider_filename(position, response)
        _write_json(provider_dir / filename, response)
        index.append(
            {
                "file": f"provider_responses/{filename}",
                "provider": response.get("provider"),
                "url": response.get("url"),
                "params": response.get("params", {}),
            }
        )
    _write_json(run_dir / "provider_responses_index.json", index)
    return run_dir


def _run_dir(base_dir: str, ticker: str, job_id: str | None) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = job_id or uuid4().hex[:8]
    return Path(base_dir) / f"{ticker.upper()}_{timestamp}_{suffix}"


def _metadata(ticker: str, question: str, state: dict[str, Any], job_id: str | None) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "ticker": ticker.upper(),
        "question": question,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "iterations": state.get("iterations", 0),
        "verification_passed": state.get("verification_passed", False),
        "unsupported_claims": state.get("unsupported_claims", []),
    }


def _provider_filename(position: int, response: dict[str, Any]) -> str:
    provider = _slug(response.get("provider", "provider"))
    endpoint = _endpoint_slug(response)
    return f"{position:03d}_{provider}_{endpoint}.json"


def _endpoint_slug(response: dict[str, Any]) -> str:
    params = response.get("params") or {}
    if params.get("function"):
        return _slug(str(params["function"]))
    url = str(response.get("url", "")).rstrip("/")
    if not url:
        return "response"
    return _slug(url.split("/")[-1] or "response")


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return slug[:80] or "item"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_jsonable(value), indent=2, ensure_ascii=True), encoding="utf-8")


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(child) for child in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
