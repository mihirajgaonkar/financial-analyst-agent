import json
import re
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from financial_research.schemas.financials import FinancialMetric
from financial_research.schemas.reports import MacroIndicator, ResearchReport, ResearchSource

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


def build_report(state: dict[str, Any], final_text: str) -> ResearchReport:
    """Convert raw tool payloads into the stable API report consumed by the UI."""
    results = state.get("tool_results", [])
    facts: dict[str, Any] = {}
    history: dict[str, Any] = {}
    quote: dict[str, Any] = {}
    company_name = state.get("ticker", "")
    macro_indicators: list[MacroIndicator] = []
    filings: list[ResearchSource] = []
    reported_facts: list[str] = []
    for result in results:
        name = result.get("name") or ""
        content = result.get("content")
        if name == "get_company_facts" and isinstance(content, dict):
            facts = content.get("facts", {})
            history = content.get("historical_facts", {})
        elif name == "get_stock_price" and isinstance(content, dict):
            quote = content
        elif name in {"get_company_profile", "get_company_overview"} and isinstance(content, dict):
            company_name = content.get("company_name") or content.get("name") or company_name
        _walk_for_macro(content, macro_indicators)
        _walk_for_filings(content, name, filings)

    metrics = list(state.get("calculated_metrics", []))
    metric_names = {metric.name for metric in metrics}
    if isinstance(quote.get("price"), int | float):
        metrics.insert(0, _metric("price", quote["price"], "USD", "latest quote", "get_stock_price"))
    current_revenue = facts.get("revenue")
    revenue_history = history.get("revenue", [])
    if "revenue_growth" not in metric_names and len(revenue_history) >= 2:
        current, prior = revenue_history[0]["value"], revenue_history[1]["value"]
        if prior:
            metrics.append(_metric("revenue_growth", (current - prior) / prior, "%", revenue_history[0]["end"], "SEC Company Facts", calculated=True))
    if isinstance(current_revenue, (int, float)):
        reported_facts.append(f"Revenue: {current_revenue:,.0f} USD")
    for name, label in (("net_income", "Net income"), ("gross_profit", "Gross profit"), ("operating_income", "Operating income")):
        if isinstance(facts.get(name), (int, float)):
            reported_facts.append(f"{label}: {facts[name]:,.0f} USD")
    if "operating_margin" not in metric_names and all(isinstance(facts.get(key), (int, float)) for key in ("operating_income", "revenue")) and facts["revenue"]:
        metrics.append(_metric("operating_margin", facts["operating_income"] / facts["revenue"], "%", "latest reported period", "SEC Company Facts", calculated=True))
    if "pe_ratio" not in metric_names and isinstance(quote.get("price"), (int, float)) and isinstance(facts.get("eps"), (int, float)) and facts["eps"] > 0:
        metrics.append(_metric("pe_ratio", quote["price"] / facts["eps"], "x", "latest quote / reported EPS", "Market quote + SEC Company Facts", calculated=True))
    calculated = _first_metrics_by_name(metrics)
    growth = _section_text("Growth", calculated, "revenue_growth", "Revenue growth could not be calculated from two annual SEC periods.")
    profitability = _section_text("Profitability", calculated, "operating_margin", "Operating margin could not be calculated from the available SEC facts.")
    valuation = _section_text("Valuation", calculated, "pe_ratio", "P/E was not calculated because price and EPS were not both available.")
    return ResearchReport(
        ticker=state["ticker"], company_name=company_name, executive_summary=final_text,
        reported_facts=reported_facts, calculated_metrics=metrics, key_financials=list(calculated.values()),
        growth_analysis=growth, profitability_analysis=profitability, valuation_analysis=valuation,
        llm_interpretation=final_text, sources=extract_sources(results), filings=filings,
        macro_indicators=macro_indicators,
    )


def _metric(name: str, value: float, unit: str | None, period: str, source: str, calculated: bool = False) -> FinancialMetric:
    return FinancialMetric(name=name, value=float(value), unit=unit, period=period, source=source, calculated=calculated)


def _first_metrics_by_name(metrics: list[FinancialMetric]) -> dict[str, FinancialMetric]:
    """Keep the first occurrence for summary sections while preserving history elsewhere."""
    unique: dict[str, FinancialMetric] = {}
    for metric in metrics:
        unique.setdefault(metric.name, metric)
    return unique


def _section_text(title: str, metrics: dict[str, FinancialMetric], key: str, missing: str) -> str:
    metric = metrics.get(key)
    if not metric:
        return f"{title}: {missing}"
    value = metric.value * 100 if metric.unit == "%" else metric.value
    suffix = "%" if metric.unit == "%" else (f" {metric.unit}" if metric.unit else "")
    return f"{title}: {value:.1f}{suffix} ({metric.period or 'reported period'}). Source: {metric.source or 'verified tool output'}."


def _walk_for_macro(value: Any, output: list[MacroIndicator]) -> None:
    if isinstance(value, dict):
        if {"series_id", "name", "value", "date"}.issubset(value):
            try:
                output.append(MacroIndicator.model_validate(value))
            except ValueError:
                pass
        for child in value.values():
            _walk_for_macro(child, output)
    elif isinstance(value, list):
        for child in value:
            _walk_for_macro(child, output)


def _walk_for_filings(value: Any, source_type: str, output: list[ResearchSource]) -> None:
    if isinstance(value, dict):
        if value.get("form") and value.get("url"):
            output.append(ResearchSource(source_type="sec_filing", title=str(value["form"]), url=value["url"]))
        for child in value.values():
            _walk_for_filings(child, source_type, output)
    elif isinstance(value, list):
        for child in value:
            _walk_for_filings(child, source_type, output)


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
                metrics.append(
                    FinancialMetric(
                        name=name,
                        value=float(value),
                        unit=_calculated_metric_unit(name),
                        source=result.get("name"),
                        calculated=True,
                    )
                )
    return metrics


def _calculated_metric_unit(name: str) -> str | None:
    if name in {"revenue_growth", "cagr", "gross_margin", "operating_margin", "net_margin"}:
        return "%"
    if name in {"pe_ratio", "price_to_sales", "ev_to_ebitda", "debt_to_equity"}:
        return "x"
    return None


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
        url = value.get("url") or value.get("source_url")
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
