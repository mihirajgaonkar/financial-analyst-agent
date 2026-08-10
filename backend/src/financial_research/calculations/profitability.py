def gross_margin(gross_profit: float, revenue: float) -> float:
    return _ratio(gross_profit, revenue, "revenue")


def operating_margin(operating_income: float, revenue: float) -> float:
    return _ratio(operating_income, revenue, "revenue")


def net_margin(net_income: float, revenue: float) -> float:
    return _ratio(net_income, revenue, "revenue")


def free_cash_flow(operating_cash_flow: float, capital_expenditures: float) -> float:
    return operating_cash_flow - abs(capital_expenditures)


def debt_to_equity(total_debt: float, total_equity: float) -> float:
    return _ratio(total_debt, total_equity, "total_equity")


def roic(nopat: float, invested_capital: float) -> float:
    return _ratio(nopat, invested_capital, "invested_capital")


def _ratio(numerator: float, denominator: float, denominator_name: str) -> float:
    if denominator == 0:
        raise ValueError(f"{denominator_name} cannot be zero.")
    return numerator / denominator
