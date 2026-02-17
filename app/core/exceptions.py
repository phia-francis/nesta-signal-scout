"""Custom exceptions for Signal Scout."""

from __future__ import annotations


class SignalScoutError(Exception):
    """Base exception for all Signal Scout errors."""
    pass


class APIError(SignalScoutError):
    """Base exception for external API failures."""
    pass


class SearchAPIError(APIError):
    """Raised when Google Search API fails."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class OpenAlexAPIError(APIError):
    """Raised when OpenAlex API fails."""
    pass


class LLMServiceError(APIError):
    """Raised when OpenAI/LLM service fails."""

    def __init__(self, message: str, model: str | None = None):
        self.model = model
        super().__init__(message)


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, service: str, retry_after: int | None = None):
        self.service = service
        self.retry_after = retry_after
        super().__init__(f"{service} rate limit exceeded")


class ValidationError(SignalScoutError):
    """Raised when input validation fails."""
    pass


class DatabaseError(SignalScoutError):
    """Raised when database operations fail."""
    pass


class ThemeClusteringError(SignalScoutError):
    """Raised when theme clustering fails."""
    pass
