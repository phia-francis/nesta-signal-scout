"""
Tests for Research Mode card improvements: scores, sources, titles.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from app.services.llm_svc import LLMService


@pytest.fixture
def mock_settings():
    """Create mock settings with API key."""
    settings = Mock()
    settings.OPENAI_API_KEY = "test_key"
    settings.CHAT_MODEL = "gpt-4o-mini"
    return settings


@pytest.mark.asyncio
async def test_generate_signal_includes_final_score(mock_settings):
    """Test that generate_signal returns a non-zero final_score."""
    service = LLMService(settings=mock_settings)

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Synthesis content."

    service.client = AsyncMock()
    service.client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await service.generate_signal(
        context="Source: snippet",
        system_prompt="Synthesize.",
        mode="Research",
    )

    assert "final_score" in result
    assert result["final_score"] > 0


@pytest.mark.asyncio
async def test_generate_signal_fallback_includes_final_score():
    """Test that fallback response also includes final_score."""
    settings = Mock()
    settings.OPENAI_API_KEY = None
    settings.CHAT_MODEL = "gpt-4o-mini"
    service = LLMService(settings=settings)

    result = await service.generate_signal(
        context="Source: snippet",
        system_prompt="Synthesize.",
        mode="Research",
    )

    assert "final_score" in result
    assert isinstance(result["final_score"], (int, float))
