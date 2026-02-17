"""
Tests for custom exception hierarchy in app.core.exceptions.
"""
from __future__ import annotations

import pytest

from app.core.exceptions import (
    SignalScoutError,
    APIError,
    SearchAPIError,
    OpenAlexAPIError,
    LLMServiceError,
    RateLimitError,
    ValidationError,
    DatabaseError,
    ThemeClusteringError,
)


class TestExceptionHierarchy:
    """Verify inheritance relationships in the exception hierarchy."""

    def test_all_exceptions_inherit_from_signal_scout_error(self):
        for exc_cls in (
            APIError, SearchAPIError, OpenAlexAPIError, LLMServiceError,
            RateLimitError, ValidationError, DatabaseError, ThemeClusteringError,
        ):
            assert issubclass(exc_cls, SignalScoutError)

    def test_api_errors_inherit_from_api_error(self):
        for exc_cls in (SearchAPIError, OpenAlexAPIError, LLMServiceError, RateLimitError):
            assert issubclass(exc_cls, APIError)

    def test_signal_scout_error_is_exception(self):
        assert issubclass(SignalScoutError, Exception)


class TestSearchAPIError:
    def test_with_status_code(self):
        err = SearchAPIError("Not found", status_code=404)
        assert str(err) == "Not found"
        assert err.status_code == 404

    def test_without_status_code(self):
        err = SearchAPIError("Network error")
        assert err.status_code is None

    def test_catchable_as_api_error(self):
        with pytest.raises(APIError):
            raise SearchAPIError("fail", status_code=500)


class TestRateLimitError:
    def test_attributes(self):
        err = RateLimitError(service="Google Search", retry_after=30)
        assert err.service == "Google Search"
        assert err.retry_after == 30
        assert "Google Search rate limit exceeded" in str(err)

    def test_without_retry_after(self):
        err = RateLimitError(service="OpenAlex")
        assert err.retry_after is None

    def test_catchable_as_api_error(self):
        with pytest.raises(APIError):
            raise RateLimitError(service="test")


class TestLLMServiceError:
    def test_with_model(self):
        err = LLMServiceError("synthesis failed", model="gpt-4o")
        assert str(err) == "synthesis failed"
        assert err.model == "gpt-4o"

    def test_without_model(self):
        err = LLMServiceError("failed")
        assert err.model is None

    def test_catchable_as_api_error(self):
        with pytest.raises(APIError):
            raise LLMServiceError("fail")


class TestBackwardCompatibility:
    """Ensure backward-compatible aliases still work."""

    def test_service_error_alias(self):
        from app.services.search_svc import ServiceError
        assert ServiceError is SearchAPIError

    def test_rate_limit_from_search_svc(self):
        from app.services.search_svc import RateLimitError as RL
        assert RL is RateLimitError
