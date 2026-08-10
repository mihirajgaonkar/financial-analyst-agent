class FinancialResearchError(Exception):
    """Base application exception."""


class ExternalServiceError(FinancialResearchError):
    """Raised when an external data provider fails."""


class InvalidTickerError(FinancialResearchError):
    """Raised when a ticker cannot be resolved."""
