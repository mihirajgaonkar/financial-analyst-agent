from langchain.tools import tool

from financial_research.calculations import (
    cagr,
    debt_to_equity,
    ev_to_ebitda,
    gross_margin,
    net_margin,
    operating_margin,
    pe_ratio,
    price_to_sales,
    yoy_growth,
)


@tool
def calculate_revenue_growth(current_revenue: float, prior_revenue: float) -> dict[str, float]:
    """Calculate year-over-year revenue growth from current and prior revenue values."""
    return {"revenue_growth": yoy_growth(current_revenue, prior_revenue)}


@tool
def calculate_cagr(beginning_value: float, ending_value: float, periods: float) -> dict[str, float]:
    """Calculate compound annual growth rate from beginning value, ending value, and number of periods."""
    return {"cagr": cagr(beginning_value, ending_value, periods)}


@tool
def calculate_margins(
    revenue: float,
    gross_profit: float | None = None,
    operating_income: float | None = None,
    net_income: float | None = None,
) -> dict[str, float]:
    """Calculate gross, operating, and net margins where sufficient inputs are provided."""
    results: dict[str, float] = {}
    if gross_profit is not None:
        results["gross_margin"] = gross_margin(gross_profit, revenue)
    if operating_income is not None:
        results["operating_margin"] = operating_margin(operating_income, revenue)
    if net_income is not None:
        results["net_margin"] = net_margin(net_income, revenue)
    return results


@tool
def calculate_pe(price: float, earnings_per_share: float) -> dict[str, float]:
    """Calculate price-to-earnings ratio from share price and earnings per share."""
    return {"pe_ratio": pe_ratio(price, earnings_per_share)}


@tool
def calculate_price_to_sales(market_cap: float, revenue: float) -> dict[str, float]:
    """Calculate price-to-sales ratio from market capitalization and revenue."""
    return {"price_to_sales": price_to_sales(market_cap, revenue)}


@tool
def calculate_ev_ebitda(enterprise_value: float, ebitda: float) -> dict[str, float]:
    """Calculate EV/EBITDA from enterprise value and EBITDA."""
    return {"ev_to_ebitda": ev_to_ebitda(enterprise_value, ebitda)}


@tool
def calculate_debt_to_equity(total_debt: float, total_equity: float) -> dict[str, float]:
    """Calculate debt-to-equity ratio from total debt and total equity."""
    return {"debt_to_equity": debt_to_equity(total_debt, total_equity)}
