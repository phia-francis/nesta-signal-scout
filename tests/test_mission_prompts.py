"""
Tests for dynamic mission-aware AI prompt generation.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from app.core.prompts import get_system_instructions


def test_get_system_instructions_cross_cutting():
    """Test that 'Any' mission triggers cross-cutting prompt."""
    prompt = get_system_instructions("Any")

    assert "Cross-Cutting" in prompt
    assert "Horizon Scanning" in prompt
    assert "broadly across all sectors" in prompt
    assert "General purpose technologies" in prompt
    assert "Intersecting trends" in prompt


def test_get_system_instructions_specific_mission():
    """Test that a specific mission focuses the prompt."""
    prompt = get_system_instructions("A Healthy Life")

    assert "A Healthy Life" in prompt
    assert "Strictly evaluate" in prompt
    assert "Cross-Cutting" not in prompt


def test_get_system_instructions_another_mission():
    """Test a different specific mission."""
    prompt = get_system_instructions("A Sustainable Future")

    assert "A Sustainable Future" in prompt
    assert "Strictly evaluate" in prompt


def test_get_system_instructions_always_has_rules():
    """Test that rules are always included regardless of mission."""
    for mission in ["Any", "A Healthy Life", "A Fairer Start"]:
        prompt = get_system_instructions(mission)
        assert "No hallucinations" in prompt
        assert "British English" in prompt
        assert "JSON" in prompt


def test_get_system_instructions_always_has_base_persona():
    """Test that base persona is always included."""
    for mission in ["Any", "A Healthy Life"]:
        prompt = get_system_instructions(mission)
        assert "Nesta Signal Scout" in prompt
        assert "Weak Signals" in prompt


@pytest.mark.asyncio
async def test_synthesize_research_uses_mission_prompt():
    """Test that synthesize_research passes mission to system prompt."""
    from app.services.llm_svc import LLMService

    settings = Mock()
    settings.OPENAI_API_KEY = "test_key"
    settings.CHAT_MODEL = "gpt-4o-mini"

    service = LLMService(settings=settings)

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"synthesis": "Test", "signals": []}'

    service.client = AsyncMock()
    service.client.chat.completions.create = AsyncMock(return_value=mock_response)

    await service.synthesize_research(
        "AI in healthcare",
        [{"title": "Test", "snippet": "Summary"}],
        mission="A Healthy Life",
    )

    # Verify the system prompt contains mission-specific content
    call_args = service.client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    system_msg = messages[0]["content"]
    assert "A Healthy Life" in system_msg
    assert "Strictly evaluate" in system_msg


@pytest.mark.asyncio
async def test_synthesize_research_cross_cutting_prompt():
    """Test that synthesize_research uses cross-cutting prompt for 'Any'."""
    from app.services.llm_svc import LLMService

    settings = Mock()
    settings.OPENAI_API_KEY = "test_key"
    settings.CHAT_MODEL = "gpt-4o-mini"

    service = LLMService(settings=settings)

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"synthesis": "Test", "signals": []}'

    service.client = AsyncMock()
    service.client.chat.completions.create = AsyncMock(return_value=mock_response)

    await service.synthesize_research(
        "general innovation",
        [{"title": "Test", "snippet": "Summary"}],
        mission="Any",
    )

    call_args = service.client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    system_msg = messages[0]["content"]
    assert "Cross-Cutting" in system_msg
    assert "broadly across all sectors" in system_msg


@pytest.mark.asyncio
async def test_synthesize_research_default_mission_is_any():
    """Test that omitting mission defaults to 'Any' (cross-cutting)."""
    from app.services.llm_svc import LLMService

    settings = Mock()
    settings.OPENAI_API_KEY = "test_key"
    settings.CHAT_MODEL = "gpt-4o-mini"

    service = LLMService(settings=settings)

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"synthesis": "Test", "signals": []}'

    service.client = AsyncMock()
    service.client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Call without mission parameter
    await service.synthesize_research(
        "test query",
        [{"title": "Test", "snippet": "Summary"}],
    )

    call_args = service.client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    system_msg = messages[0]["content"]
    assert "Cross-Cutting" in system_msg
