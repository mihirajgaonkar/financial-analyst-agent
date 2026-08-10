def discount_cash_flow(cash_flow: float, discount_rate: float, period: int) -> float:
    if period <= 0:
        raise ValueError("period must be positive.")
    if discount_rate <= -1:
        raise ValueError("discount_rate must be greater than -100%.")
    return cash_flow / ((1 + discount_rate) ** period)


def terminal_value(final_cash_flow: float, discount_rate: float, perpetual_growth_rate: float) -> float:
    if discount_rate <= perpetual_growth_rate:
        raise ValueError("discount_rate must exceed perpetual_growth_rate.")
    return final_cash_flow * (1 + perpetual_growth_rate) / (discount_rate - perpetual_growth_rate)
