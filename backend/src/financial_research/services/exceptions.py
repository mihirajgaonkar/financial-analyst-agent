class FinancialResearchError(Exception):
    """Base application exception."""


class ExternalServiceError(FinancialResearchError):
    """Raised when an external data provider fails."""


class RateLimitError(ExternalServiceError):
    """Raised when an external provider rejects a request due to quota or rate limits."""


class InvalidTickerError(FinancialResearchError):
    """Raised when a ticker cannot be resolved."""
