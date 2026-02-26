"""
Tests for novelty query enhancement and trend modifiers.
"""
from __future__ import annotations

import pytest
import respx
from httpx import Response
from unittest.mock import AsyncMock, Mock, patch

from app import keywords
from app.services.scan_logic import build_novelty_query


def test_get_trend_modifiers_returns_list():
    """Test that get_trend_modifiers returns a list of modifier strings."""
    modifiers = keywords.get_trend_modifiers("alternative proteins")
    assert isinstance(modifiers, list)
    assert len(modifiers) > 0
    assert all(isinstance(m, str) for m in modifiers)


def test_get_trend_modifiers_returns_top_five():
    """Test that get_trend_modifiers returns exactly 5 modifiers."""
    modifiers = keywords.get_trend_modifiers("quantum computing")
    assert len(modifiers) == 5


def test_novelty_modifiers_constant_exists():
    """Test that NOVELTY_MODIFIERS constant is defined."""
    assert hasattr(keywords, "NOVELTY_MODIFIERS")
    assert isinstance(keywords.NOVELTY_MODIFIERS, list)
    assert len(keywords.NOVELTY_MODIFIERS) > 0


def test_build_novelty_query_appends_modifiers():
    """Test that build_novelty_query adds OR-joined modifiers."""
    result = build_novelty_query("alternative proteins")
    assert result.startswith("alternative proteins (")
    assert " OR " in result
    assert result.endswith(")")


def test_build_novelty_query_contains_expected_terms():
    """Test that the enhanced query contains expected modifier terms."""
    result = build_novelty_query("climate tech")
    for term in ["pilot", "trial", "prototype", "emerging", "startup"]:
        assert term in result


def test_build_novelty_query_preserves_original():
    """Test that the original query is preserved in the enhanced version."""
    result = build_novelty_query("heat pumps UK")
    assert "heat pumps UK" in result


def test_build_novelty_query_handles_empty_modifiers():
    """Test fallback when no modifiers are available."""
    with patch.object(keywords, "get_trend_modifiers", return_value=[]):
        result = build_novelty_query("test query")
    assert result == "test query"


@pytest.mark.asyncio
@respx.mock
async def test_search_with_sort_by_date():
    """Test that sort_by_date parameter adds sort=date to API call."""
    from app.core.config import Settings
    from app.services.search_svc import SearchService

    settings = Settings()
    settings.GOOGLE_SEARCH_API_KEY = "test_key"
    settings.GOOGLE_SEARCH_CX = "test_cx"
    service = SearchService(settings=settings)

    mock_response = {"items": [{"title": "Recent", "link": "https://example.com"}]}
    route = respx.get("https://www.googleapis.com/customsearch/v1").mock(
        return_value=Response(200, json=mock_response)
    )

    await service.search("test query", num=5, freshness="month", sort_by_date=True)

    assert route.called
    request = route.calls[0].request
    assert "sort=date" in str(request.url)
    assert "dateRestrict=m1" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_search_without_sort_by_date():
    """Test that sort parameter is absent when sort_by_date is False."""
    from app.core.config import Settings
    from app.services.search_svc import SearchService

    settings = Settings()
    settings.GOOGLE_SEARCH_API_KEY = "test_key"
    settings.GOOGLE_SEARCH_CX = "test_cx"
    service = SearchService(settings=settings)

    mock_response = {"items": [{"title": "Result", "link": "https://example.com"}]}
    route = respx.get("https://www.googleapis.com/customsearch/v1").mock(
        return_value=Response(200, json=mock_response)
    )

    await service.search("test query", num=5, freshness="month", sort_by_date=False)

    assert route.called
    request = route.calls[0].request
    assert "sort=date" not in str(request.url)


def test_radar_prompt_contains_encyclopedic_penalties():
    """Test that RADAR_SYSTEM_PROMPT includes encyclopedic content penalties."""
    from app.core.prompts import RADAR_SYSTEM_PROMPT

    assert "Wikipedia" in RADAR_SYSTEM_PROMPT
    assert "Britannica" in RADAR_SYSTEM_PROMPT
    assert "Score < 3.0" in RADAR_SYSTEM_PROMPT
    assert "PENALIZE ENCYCLOPEDIC CONTENT" in RADAR_SYSTEM_PROMPT


def test_radar_prompt_contains_recency_rubric():
    """Test that RADAR_SYSTEM_PROMPT includes recency scoring rubric."""
    from app.core.prompts import RADAR_SYSTEM_PROMPT

    assert "Recency Multiplier" in RADAR_SYSTEM_PROMPT
    assert "Novelty Factor" in RADAR_SYSTEM_PROMPT
    assert "Score >= 5.0" in RADAR_SYSTEM_PROMPT


def test_radar_prompt_retains_original_purpose():
    """Test that the updated prompt still identifies weak signals."""
    from app.core.prompts import RADAR_SYSTEM_PROMPT

    assert "weak signals" in RADAR_SYSTEM_PROMPT.lower()
    assert "novelty" in RADAR_SYSTEM_PROMPT.lower()
