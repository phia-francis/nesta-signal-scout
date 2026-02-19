"""
Tests for LLMService stateless context-aware functionality.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.llm_svc import LLMService


@pytest.fixture
def mock_settings():
    """Create mock settings with API key."""
    settings = Mock()
    settings.OPENAI_API_KEY = "test_key"
    settings.CHAT_MODEL = "gpt-4o-mini"
    return settings


@pytest.fixture
def llm_service_with_key(mock_settings):
    """Create LLMService with mock settings."""
    return LLMService(settings=mock_settings)


def test_llm_service_without_api_key():
    """Test that LLMService handles missing API key gracefully."""
    settings = Mock()
    settings.OPENAI_API_KEY = None
    settings.CHAT_MODEL = "gpt-4o-mini"
    
    service = LLMService(settings=settings)
    
    assert service.client is None
    assert service.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_synthesize_research_without_client():
    """Test that synthesize_research returns fallback when no client."""
    settings = Mock()
    settings.OPENAI_API_KEY = None
    settings.CHAT_MODEL = "gpt-4o-mini"
    
    service = LLMService(settings=settings)
    
    result = await service.synthesize_research("test query", [{"title": "Test"}])
    
    assert "synthesis" in result
    assert "unavailable" in result["synthesis"].lower()


@pytest.mark.asyncio
async def test_synthesize_research_with_empty_results(llm_service_with_key):
    """Test that synthesize_research handles empty search results."""
    result = await llm_service_with_key.synthesize_research("test query", [])
    
    assert "synthesis" in result
    assert "No data found" in result["synthesis"]


@pytest.mark.asyncio
async def test_synthesize_research_success(llm_service_with_key):
    """Test successful LLM synthesis with mocked OpenAI response."""
    # Mock the OpenAI client response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"synthesis": "Test synthesis", "signals": ["signal1", "signal2"]}'
    
    llm_service_with_key.client = AsyncMock()
    llm_service_with_key.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    search_results = [
        {"title": "Result 1", "snippet": "Summary 1", "displayLink": "source1.com"},
        {"title": "Result 2", "snippet": "Summary 2", "displayLink": "source2.com"}
    ]
    
    result = await llm_service_with_key.synthesize_research("quantum computing", search_results)
    
    assert result["synthesis"] == "Test synthesis"
    assert len(result["signals"]) == 2
    assert llm_service_with_key.client.chat.completions.create.called


@pytest.mark.asyncio
async def test_synthesize_research_error_handling(llm_service_with_key):
    """Test that synthesize_research raises LLMServiceError on API errors."""
    from app.core.exceptions import LLMServiceError

    llm_service_with_key.client = AsyncMock()
    llm_service_with_key.client.chat.completions.create = AsyncMock(
        side_effect=Exception("API Error")
    )
    
    search_results = [{"title": "Test", "snippet": "Summary"}]
    
    with pytest.raises(LLMServiceError) as exc_info:
        await llm_service_with_key.synthesize_research("test", search_results)
    
    assert "LLM synthesis failed" in str(exc_info.value)
    assert exc_info.value.model == "gpt-4o-mini"


def test_format_results_for_llm(llm_service_with_key):
    """Test that _format_results_for_llm formats correctly."""
    results = [
        {"title": "Title 1", "snippet": "Snippet 1", "displayLink": "source1.com"},
        {"title": "Title 2", "abstract": "Abstract 2", "source": "source2"},
    ]
    
    formatted = llm_service_with_key._format_results_for_llm(results)
    
    # Standard assertions
    assert "[1] Title 1" in formatted
    assert "[2] Title 2" in formatted
    
    # More specific assertions for CodeQL compliance
    # We check for the explicit format "(source1.com)" or "(source2)" 
    # to ensure we aren't matching substrings like "evilsource1.com"
    assert "(source1.com)" in formatted
    assert "(source2)" in formatted
    
    assert "Abstract 2" in formatted


def test_format_results_limits_to_15(llm_service_with_key):
    """Test that _format_results_for_llm limits to top 15 results."""
    results = [{"title": f"Title {i}", "snippet": f"Snippet {i}"} for i in range(20)]
    
    formatted = llm_service_with_key._format_results_for_llm(results)
    
    assert "[15]" in formatted
    assert "[16]" not in formatted


@pytest.mark.asyncio
async def test_generate_signal_without_client_returns_fallback():
    """Test that generate_signal returns fallback when no client."""
    settings = Mock()
    settings.OPENAI_API_KEY = None
    settings.CHAT_MODEL = "gpt-4o-mini"

    service = LLMService(settings=settings)

    result = await service.generate_signal(
        context="Source (http://a.com): snippet one",
        system_prompt="You are an analyst.",
        mode="Research",
    )

    assert result["title"] == "Research Synthesis"
    assert result["mode"] == "Research"
    assert "not configured" in result["summary"].lower()


@pytest.mark.asyncio
async def test_generate_signal_empty_context_raises_error(llm_service_with_key):
    """Test generate_signal raises ValueError on empty context."""
    with pytest.raises(ValueError, match="empty context"):
        await llm_service_with_key.generate_signal(
            context="", system_prompt="Synthesize.", mode="research"
        )


@pytest.mark.asyncio
async def test_generate_signal_success(llm_service_with_key):
    """Test successful generate_signal with mocked OpenAI response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "A concise synthesis of the data."

    llm_service_with_key.client = AsyncMock()
    llm_service_with_key.client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await llm_service_with_key.generate_signal(
        context="Source: snippet",
        system_prompt="Synthesize.",
        mode="Research",
    )

    assert result["summary"] == "A concise synthesis of the data."
    assert result["title"] == "Research Synthesis"
    assert llm_service_with_key.client.chat.completions.create.called


@pytest.mark.asyncio
async def test_generate_signal_api_error_raises(llm_service_with_key):
    """Test that generate_signal raises LLMServiceError on API error."""
    from app.core.exceptions import LLMServiceError

    llm_service_with_key.client = AsyncMock()
    llm_service_with_key.client.chat.completions.create = AsyncMock(
        side_effect=Exception("API Error")
    )

    with pytest.raises(LLMServiceError, match="LLM generate_signal failed"):
        await llm_service_with_key.generate_signal(
            context="Source (http://a.com): snippet one",
            system_prompt="Synthesize.",
            mode="Research",
        )
