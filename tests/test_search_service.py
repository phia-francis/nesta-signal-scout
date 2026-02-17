"""
Tests for SearchService with respx HTTP mocking.
"""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.services.search_svc import SearchService, ServiceError, RateLimitError


@pytest.fixture
def search_service():
    """Create a SearchService instance for testing."""
    from app.core.config import Settings
    settings = Settings()
    settings.GOOGLE_SEARCH_API_KEY = "test_key"
    settings.GOOGLE_SEARCH_CX = "test_cx"
    return SearchService(settings=settings)


@pytest.mark.asyncio
@respx.mock
async def test_search_successful_returns_results(search_service):
    """Test that successful search returns results."""
    # Mock the Google API response
    mock_response = {
        "items": [
            {
                "title": "Test Result 1",
                "link": "https://example.com/1",
                "snippet": "Test snippet 1"
            },
            {
                "title": "Test Result 2",
                "link": "https://example.com/2",
                "snippet": "Test snippet 2"
            }
        ]
    }
    
    respx.get("https://www.googleapis.com/customsearch/v1").mock(
        return_value=Response(200, json=mock_response)
    )
    
    results = await search_service.search("test query", num=2)
    
    assert len(results) == 2
    assert results[0]["title"] == "Test Result 1"
    assert results[1]["link"] == "https://example.com/2"


@pytest.mark.asyncio
@respx.mock
async def test_search_empty_results(search_service):
    """Test that search handles empty results."""
    mock_response = {"items": []}
    
    respx.get("https://www.googleapis.com/customsearch/v1").mock(
        return_value=Response(200, json=mock_response)
    )
    
    results = await search_service.search("rare query", num=10)
    
    assert len(results) == 0


@pytest.mark.asyncio
@respx.mock
async def test_search_handles_429_rate_limit(search_service):
    """Test that search handles 429 rate limit error with retries."""
    # First two attempts return 429, third succeeds
    respx.get("https://www.googleapis.com/customsearch/v1").mock(
        side_effect=[
            Response(429, headers={"Retry-After": "1"}),
            Response(429, headers={"Retry-After": "1"}),
            Response(429, headers={"Retry-After": "1"}),
        ]
    )
    
    with pytest.raises(RateLimitError) as exc_info:
        await search_service.search("test query", num=5, max_retries=3)
    
    assert "rate limit exceeded" in str(exc_info.value).lower()


@pytest.mark.asyncio
@respx.mock
async def test_search_handles_429_with_successful_retry(search_service):
    """Test that search successfully retries after 429."""
    mock_response = {"items": [{"title": "Success", "link": "https://example.com"}]}
    
    # First attempt 429, second succeeds
    respx.get("https://www.googleapis.com/customsearch/v1").mock(
        side_effect=[
            Response(429, headers={"Retry-After": "1"}),
            Response(200, json=mock_response),
        ]
    )
    
    results = await search_service.search("test query", num=5, max_retries=3)
    
    assert len(results) == 1
    assert results[0]["title"] == "Success"


@pytest.mark.asyncio
@respx.mock
async def test_search_handles_500_server_error(search_service):
    """Test that search handles 500 server error."""
    respx.get("https://www.googleapis.com/customsearch/v1").mock(
        return_value=Response(500, text="Internal Server Error")
    )
    
    with pytest.raises(ServiceError) as exc_info:
        await search_service.search("test query", num=5)
    
    assert "500" in str(exc_info.value)


@pytest.mark.asyncio
@respx.mock
async def test_search_handles_403_forbidden(search_service):
    """Test that search handles 403 forbidden error."""
    respx.get("https://www.googleapis.com/customsearch/v1").mock(
        return_value=Response(403, text="Forbidden")
    )
    
    with pytest.raises(ServiceError) as exc_info:
        await search_service.search("test query", num=5)
    
    assert "403" in str(exc_info.value).lower()


@pytest.mark.asyncio
@respx.mock
async def test_search_handles_400_bad_request(search_service):
    """Test that search handles 400 bad request."""
    respx.get("https://www.googleapis.com/customsearch/v1").mock(
        return_value=Response(400, text="Bad Request")
    )
    
    with pytest.raises(ServiceError) as exc_info:
        await search_service.search("test query", num=5)
    
    assert "400" in str(exc_info.value)


@pytest.mark.asyncio
async def test_search_validates_missing_api_key():
    """Test that search raises error when API keys are missing."""
    from app.core.config import Settings
    settings = Settings()
    settings.GOOGLE_SEARCH_API_KEY = None
    settings.GOOGLE_SEARCH_CX = None
    service = SearchService(settings=settings)
    
    with pytest.raises(ServiceError) as exc_info:
        await service.search("test query")
    
    assert "api key" in str(exc_info.value).lower()


@pytest.mark.asyncio
@respx.mock
async def test_search_with_freshness_parameter(search_service):
    """Test that search correctly applies freshness parameter."""
    mock_response = {"items": [{"title": "Recent", "link": "https://example.com"}]}
    
    route = respx.get("https://www.googleapis.com/customsearch/v1").mock(
        return_value=Response(200, json=mock_response)
    )
    
    await search_service.search("test query", num=5, freshness="month")
    
    # Verify the request included dateRestrict parameter
    assert route.called
    request = route.calls[0].request
    assert "dateRestrict=m1" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_search_respects_num_parameter(search_service):
    """Test that search respects the num parameter."""
    mock_response = {"items": [{"title": f"Result {i}", "link": f"https://example.com/{i}"} for i in range(10)]}
    
    respx.get("https://www.googleapis.com/customsearch/v1").mock(
        return_value=Response(200, json=mock_response)
    )
    
    results = await search_service.search("test query", num=10)
    
    assert len(results) == 10
