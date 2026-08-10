import pytest

from financial_research.calculations import (
    cagr,
    debt_to_equity,
    ev_to_ebitda,
    free_cash_flow,
    gross_margin,
    net_margin,
    operating_margin,
    pe_ratio,
    price_to_sales,
    roic,
    yoy_growth,
)


def test_growth_formulas() -> None:
    assert yoy_growth(120, 100) == pytest.approx(0.20)
    assert cagr(100, 121, 2) == pytest.approx(0.10)


def test_profitability_formulas() -> None:
    assert gross_margin(40, 100) == pytest.approx(0.40)
    assert operating_margin(25, 100) == pytest.approx(0.25)
    assert net_margin(15, 100) == pytest.approx(0.15)
    assert free_cash_flow(50, -12) == pytest.approx(38)
    assert debt_to_equity(80, 40) == pytest.approx(2)
    assert roic(18, 120) == pytest.approx(0.15)


def test_valuation_formulas() -> None:
    assert pe_ratio(150, 6) == pytest.approx(25)
    assert price_to_sales(500, 100) == pytest.approx(5)
    assert ev_to_ebitda(300, 30) == pytest.approx(10)


def test_zero_denominators_raise() -> None:
    with pytest.raises(ValueError):
        yoy_growth(100, 0)
    with pytest.raises(ValueError):
        gross_margin(1, 0)
    with pytest.raises(ValueError):
        pe_ratio(1, 0)
