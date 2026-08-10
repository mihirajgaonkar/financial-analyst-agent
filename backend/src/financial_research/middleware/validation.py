def normalize_ticker(ticker: str) -> str:
    normalized = ticker.upper().strip()
    if not normalized:
        raise ValueError("Ticker cannot be empty.")
    if len(normalized) > 16:
        raise ValueError("Ticker is too long.")
    return normalized
