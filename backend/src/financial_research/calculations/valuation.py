def pe_ratio(price: float, earnings_per_share: float) -> float:
    return _ratio(price, earnings_per_share, "earnings_per_share")


def price_to_sales(market_cap: float, revenue: float) -> float:
    return _ratio(market_cap, revenue, "revenue")


def ev_to_ebitda(enterprise_value: float, ebitda: float) -> float:
    return _ratio(enterprise_value, ebitda, "ebitda")


def _ratio(numerator: float, denominator: float, denominator_name: str) -> float:
    if denominator == 0:
        raise ValueError(f"{denominator_name} cannot be zero.")
    return numerator / denominator
