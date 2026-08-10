def yoy_growth(current: float, prior: float) -> float:
    _ensure_nonzero(prior, "prior")
    return (current - prior) / abs(prior)


def cagr(beginning: float, ending: float, periods: float) -> float:
    _ensure_positive(beginning, "beginning")
    _ensure_positive(ending, "ending")
    _ensure_positive(periods, "periods")
    return (ending / beginning) ** (1 / periods) - 1


def _ensure_nonzero(value: float, name: str) -> None:
    if value == 0:
        raise ValueError(f"{name} cannot be zero.")


def _ensure_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive.")
