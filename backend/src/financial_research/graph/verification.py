import json
import re
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from financial_research.schemas.financials import FinancialMetric
from financial_research.schemas.reports import ResearchSource

NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])\$?-?\d+(?:,\d{3})*(?:\.\d+)?%?")
CALCULATION_TOOL_NAMES = {
    "calculate_revenue_growth",
    "calculate_cagr",
    "calculate_margins",
    "calculate_pe",
    "calculate_price_to_sales",
    "calculate_ev_ebitda",
    "calculate_debt_to_equity",
}


def collect_tool_results(messages: list[Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        payload = _loads_jsonish(message.content)
        results.append(
            {
                "tool_call_id": message.tool_call_id,
                "name": getattr(message, "name", None),
                "content": payload,
            }
        )
    return results


def extract_sources(tool_results: list[dict[str, Any]]) -> list[ResearchSource]:
    sources: list[ResearchSource] = []
    for result in tool_results:
        _walk_for_sources(result.get("content"), result.get("name") or "tool", sources)
    return sources


def extract_calculated_metrics(tool_results: list[dict[str, Any]]) -> list[FinancialMetric]:
    metrics: list[FinancialMetric] = []
    for result in tool_results:
        if result.get("name") not in CALCULATION_TOOL_NAMES:
            continue
        content = result.get("content")
        if not isinstance(content, dict):
            continue
        for name, value in content.items():
            if isinstance(value, int | float):
                metrics.append(FinancialMetric(name=name, value=float(value), source=result.get("name"), calculated=True))
    return metrics


def verify_final_message(messages: list[Any], tool_results: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    final_text = _last_ai_text(messages)
    unsupported: list[str] = []
    if not final_text:
        return False, ["No final AI response was available for verification."]

    tool_text = json.dumps(tool_results, default=str)
    tool_numbers = {_normalize_number(match.group(0)) for match in NUMBER_PATTERN.finditer(tool_text)}
    final_numbers = {_normalize_number(match.group(0)) for match in NUMBER_PATTERN.finditer(final_text)}
    missing_numbers = sorted(number for number in final_numbers if number not in tool_numbers)
    if missing_numbers:
        unsupported.append(f"Numbers not found in tool results: {', '.join(missing_numbers[:10])}")

    if ("sec" in final_text.lower() or "filing" in final_text.lower()) and "Archives/edgar" not in tool_text:
        unsupported.append("SEC filing claim appears without an SEC filing source URL in tool results.")

    return not unsupported, unsupported


def _last_ai_text(messages: list[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return _message_text(message.content)
    return ""


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, default=str)


def _loads_jsonish(content: Any) -> Any:
    if not isinstance(content, str):
        return content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return content


def _walk_for_sources(value: Any, source_type: str, sources: list[ResearchSource]) -> None:
    if isinstance(value, dict):
        url = value.get("url")
        title = value.get("form") or value.get("title") or value.get("name") or source_type
        if isinstance(url, str) and url:
            sources.append(ResearchSource(source_type=source_type, title=str(title), url=url))
        for child in value.values():
            _walk_for_sources(child, source_type, sources)
    elif isinstance(value, list):
        for child in value:
            _walk_for_sources(child, source_type, sources)


def _normalize_number(value: str) -> str:
    return value.replace("$", "").replace(",", "").replace("%", "")
