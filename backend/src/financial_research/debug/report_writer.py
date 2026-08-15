"""Write human-readable diagnostics for completed research graph runs."""

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from financial_research.config.settings import get_settings


FINAL_SYNTHESIS_PROMPT = """Write the final research response now.

Use only information already returned by tools in this conversation.
Do not request additional tools.
Distinguish reported facts, calculated metrics, interpretation, limitations, and sources.
If a required figure is missing, say exactly what is missing instead of inventing it.
"""


def write_debug_report(
    state: dict[str, Any],
    ticker: str,
    question: str,
    output_dir: str,
    system_prompt: str,
    job_id: str | None = None,
    external_responses: list[dict[str, Any]] | None = None,
) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = job_id or uuid4().hex[:8]
    stem = f"{ticker.upper()}_{timestamp}_{suffix}"
    report_path = directory / f"{stem}.md"
    raw_path = directory / f"{stem}.raw.json"

    raw_responses = external_responses or []
    raw_path.write_text(json.dumps(_jsonable(raw_responses), indent=2, ensure_ascii=True), encoding="utf-8")
    report_path.write_text(
        _render_markdown(
            state=state,
            ticker=ticker,
            question=question,
            system_prompt=system_prompt,
            raw_responses=raw_responses,
            raw_path=raw_path.name,
        ),
        encoding="utf-8",
    )
    return report_path


def _render_markdown(
    state: dict[str, Any],
    ticker: str,
    question: str,
    system_prompt: str,
    raw_responses: list[dict[str, Any]],
    raw_path: str,
) -> str:
    settings = get_settings()
    messages = state.get("messages", [])
    tool_results = state.get("tool_results", [])
    report = state.get("final_report")
    metadata = {
        "ticker": ticker.upper(),
        "question": question,
        "llm_provider": settings.llm_provider,
        "llm_model": _configured_model(settings),
        "iterations": state.get("iterations", 0),
        "verification_passed": state.get("verification_passed", False),
        "unsupported_claims": state.get("unsupported_claims", []),
    }
    sections = [
        f"# Research Debug Report: {ticker.upper()}",
        "",
        "> This file is a local diagnostic artifact. It records the research inputs, tool traffic, normalized report, and verification state. API keys are redacted.",
        "",
        "## Run Metadata",
        _json_block(metadata),
        "",
        "## User Prompt",
        question.strip(),
        "",
        "## Effective Instructions",
        "### Research System Prompt",
        _text_block(system_prompt),
        "### Final Synthesis Prompt",
        _text_block(FINAL_SYNTHESIS_PROMPT),
        "",
        "## Message History Used By The Graph",
        "The system prompt is injected for each research-agent call. The entries below are the persisted LangGraph messages, including model tool calls and tool responses.",
        _message_blocks(messages),
        "",
        "## Tool Results Collected For Verification",
        _json_block(tool_results),
        "",
        "## Raw External Responses",
        f"Exact JSON responses captured from external providers are stored in [`{raw_path}`]({raw_path}). The Markdown report keeps this section compact so large provider responses do not make the report unreadable.",
        _raw_response_summary(raw_responses),
        "",
        "## Final Structured ResearchReport",
        _json_block(report.model_dump(mode="json") if hasattr(report, "model_dump") else report),
        "",
        "## Reading This Report",
        "The message history shows what was exchanged with the model. Tool results show the normalized payload made available to verification and final report construction. The raw JSON file shows the provider response before normalization. A provider response is not automatically sent to the model; only the tool return value is.",
        "",
    ]
    return "\n".join(sections)


def _message_blocks(messages: list[Any]) -> str:
    if not messages:
        return "\n_No messages recorded._\n"
    blocks: list[str] = []
    for index, message in enumerate(messages, start=1):
        record = {
            "type": getattr(message, "type", None),
            "name": getattr(message, "name", None),
            "tool_call_id": getattr(message, "tool_call_id", None),
            "content": getattr(message, "content", None),
            "tool_calls": getattr(message, "tool_calls", None),
        }
        blocks.extend([f"### Message {index}", _json_block(record)])
    return "\n" + "\n".join(blocks) + "\n"


def _raw_response_summary(responses: list[dict[str, Any]]) -> str:
    if not responses:
        return "\n_No external responses were captured._\n"
    rows = ["", "| # | Provider | Endpoint | Payload size |", "|---:|---|---|---:|"]
    for index, response in enumerate(responses, start=1):
        payload = json.dumps(_jsonable(response.get("payload")), ensure_ascii=True)
        rows.append(f"| {index} | {response.get('provider', '')} | `{response.get('url', '')}` | {len(payload):,} characters |")
    return "\n" + "\n".join(rows) + "\n"


def _configured_model(settings: Any) -> str:
    provider = settings.llm_provider.lower()
    return getattr(settings, f"{provider}_model", None) or getattr(settings, "google_model", None) or "unknown"


def _text_block(value: str) -> str:
    return f"\n```text\n{value.strip()}\n```\n"


def _json_block(value: Any) -> str:
    return f"\n```json\n{json.dumps(_jsonable(value), indent=2, ensure_ascii=True)}\n```\n"


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(child) for child in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
