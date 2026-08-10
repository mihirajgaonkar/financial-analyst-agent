from financial_research.tools.calculation_tools import (
    calculate_cagr,
    calculate_debt_to_equity,
    calculate_ev_ebitda,
    calculate_margins,
    calculate_pe,
    calculate_price_to_sales,
    calculate_revenue_growth,
)
from financial_research.tools.macro_tools import create_macro_tools
from financial_research.tools.market_tools import create_market_tools
from financial_research.tools.sec_tools import create_sec_tools


def create_research_tools():
    return [
        *create_sec_tools(),
        *create_market_tools(),
        *create_macro_tools(),
        calculate_revenue_growth,
        calculate_cagr,
        calculate_margins,
        calculate_pe,
        calculate_price_to_sales,
        calculate_ev_ebitda,
        calculate_debt_to_equity,
    ]


__all__ = [
    "calculate_cagr",
    "calculate_debt_to_equity",
    "calculate_ev_ebitda",
    "calculate_margins",
    "calculate_pe",
    "calculate_price_to_sales",
    "calculate_revenue_growth",
    "create_macro_tools",
    "create_market_tools",
    "create_research_tools",
    "create_sec_tools",
]
