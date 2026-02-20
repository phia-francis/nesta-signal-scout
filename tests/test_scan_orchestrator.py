"""
Tests for ScanOrchestrator with mocked services.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.domain.models import RawSignal, SignalCard
from app.services.scan_logic import ScanOrchestrator


@pytest.fixture
def mock_services():
    """Create mock services for ScanOrchestrator."""
    gateway_service = Mock()
    gateway_service.fetch_projects = AsyncMock(return_value=[])
    
    openalex_service = Mock()
    openalex_service.search_works = AsyncMock(return_value=[])
    
    search_service = Mock()
    search_service.search = AsyncMock(return_value=[
        {"title": "Test", "link": "https://example.com", "snippet": "Test snippet"}
    ])
    
    analytics_service = Mock()
    analytics_service.calculate_recency_score = Mock(return_value=5.0)
    analytics_service.classify_sweet_spot = Mock(return_value="Nascent")
    
    taxonomy = Mock()

    llm_service = Mock()
    llm_service.generate_agentic_queries = AsyncMock(
        return_value=["test emerging trends", "test global policy", "test breakthrough"]
    )
    llm_service.verify_and_synthesize = AsyncMock(return_value=[
        {"title": "Verified Signal", "summary": "A verified summary.", "url": "https://example.com", "score": 7.5}
    ])
    llm_service.client = True  # Simulate available client
    
    return {
        "gateway": gateway_service,
        "openalex": openalex_service,
        "search": search_service,
        "analytics": analytics_service,
        "taxonomy": taxonomy,
        "llm": llm_service,
    }


@pytest.fixture
def orchestrator(mock_services):
    """Create ScanOrchestrator with mocked services."""
    return ScanOrchestrator(
        gateway_service=mock_services["gateway"],
        openalex_service=mock_services["openalex"],
        search_service=mock_services["search"],
        analytics_service=mock_services["analytics"],
        taxonomy=mock_services["taxonomy"],
        llm_service=mock_services["llm"],
    )


@pytest.mark.asyncio
async def test_execute_scan_radar_mode(orchestrator, mock_services):
    """Test that execute_scan returns signals with proper structure in radar mode."""
    result = await orchestrator.execute_scan("AI innovation", "A Healthy Life", "radar")

    assert "signals" in result
    assert "warnings" in result
    assert "mode" in result
    assert result["mode"] == "radar"
    assert isinstance(result["signals"], list)


@pytest.mark.asyncio
async def test_execute_scan_research_mode(orchestrator, mock_services):
    """Test that execute_scan works in research mode."""
    result = await orchestrator.execute_scan("quantum computing", "A Sustainable Future", "research")

    assert result["mode"] == "research"
    assert "signals" in result
    assert "related_terms" in result


@pytest.mark.asyncio
async def test_execute_scan_governance_mode(orchestrator, mock_services):
    """Test that execute_scan works in governance mode."""
    result = await orchestrator.execute_scan("climate policy", "A Sustainable Future", "governance")

    assert result["mode"] == "governance"
    assert "signals" in result


@pytest.mark.asyncio
async def test_execute_scan_invalid_mode_defaults_to_radar(orchestrator, mock_services):
    """Test that an invalid mode defaults to radar."""
    result = await orchestrator.execute_scan("test query", "General", "invalid_mode")

    assert result["mode"] == "radar"


@pytest.mark.asyncio
async def test_execute_scan_empty_query_raises_validation_error(orchestrator, mock_services):
    """Test that execute_scan raises ValidationError for empty query."""
    from app.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        await orchestrator.execute_scan("", "General", "radar")


@pytest.mark.asyncio
async def test_execute_scan_returns_signal_cards(orchestrator, mock_services):
    """Test that execute_scan returns SignalCard objects."""
    result = await orchestrator.execute_scan("AI innovation", "A Healthy Life", "radar")

    assert "signals" in result
    for s in result["signals"]:
        assert isinstance(s, SignalCard)


@pytest.mark.asyncio
async def test_execute_scan_calls_generate_agentic_queries(orchestrator, mock_services):
    """Test that execute_scan calls llm_service.generate_agentic_queries."""
    await orchestrator.execute_scan("AI innovation", "A Healthy Life", "radar")

    mock_services["llm"].generate_agentic_queries.assert_called_once_with(
        topic="AI innovation",
        mode="radar",
        mission="A Healthy Life",
        num_queries=3,
    )


@pytest.mark.asyncio
async def test_execute_scan_calls_verify_and_synthesize(orchestrator, mock_services):
    """Test that execute_scan calls llm_service.verify_and_synthesize."""
    await orchestrator.execute_scan("AI innovation", "A Healthy Life", "radar")

    assert mock_services["llm"].verify_and_synthesize.called


@pytest.mark.asyncio
async def test_execute_scan_research_uses_six_queries(orchestrator, mock_services):
    """Test that research mode requests 6 queries."""
    await orchestrator.execute_scan("quantum computing", "General", "research")

    mock_services["llm"].generate_agentic_queries.assert_called_once_with(
        topic="quantum computing",
        mode="research",
        mission="General",
        num_queries=6,
    )


@pytest.mark.asyncio
async def test_execute_scan_governance_uses_three_queries(orchestrator, mock_services):
    """Test that governance mode requests 3 queries."""
    await orchestrator.execute_scan("climate policy", "General", "governance")

    mock_services["llm"].generate_agentic_queries.assert_called_once_with(
        topic="climate policy",
        mode="governance",
        mission="General",
        num_queries=3,
    )


@pytest.mark.asyncio
async def test_execute_scan_handles_search_failures(orchestrator, mock_services):
    """Test that execute_scan handles search failures gracefully."""
    mock_services["search"].search = AsyncMock(side_effect=Exception("API error"))

    result = await orchestrator.execute_scan("test query", "General", "radar")

    # Should still return a valid result structure
    assert "signals" in result
    assert isinstance(result["signals"], list)


@pytest.mark.asyncio
async def test_execute_scan_deduplicates_by_url(orchestrator, mock_services):
    """Test that execute_scan deduplicates results by URL before verification."""
    mock_services["search"].search = AsyncMock(return_value=[
        {"title": "Test 1", "link": "https://example.com/same", "snippet": "Snippet 1"},
        {"title": "Test 2", "link": "https://example.com/same", "snippet": "Snippet 2"},
        {"title": "Test 3", "link": "https://example.com/different", "snippet": "Snippet 3"},
    ])

    await orchestrator.execute_scan("test query", "General", "radar")

    # verify_and_synthesize should receive deduplicated results
    call_args = mock_services["llm"].verify_and_synthesize.call_args
    raw_results = call_args.kwargs.get("raw_results") or call_args[1].get("raw_results") or call_args[0][0]
    assert len(raw_results) == 2  # Deduplicated


@pytest.mark.asyncio
async def test_execute_scan_sorts_by_score(orchestrator, mock_services):
    """Test that execute_scan sorts results by final_score descending."""
    mock_services["llm"].verify_and_synthesize = AsyncMock(return_value=[
        {"title": "Low Score", "summary": "Low", "url": "https://example.com/low", "score": 3.0},
        {"title": "High Score", "summary": "High", "url": "https://example.com/high", "score": 9.0},
    ])

    result = await orchestrator.execute_scan("test query", "General", "radar")

    if len(result["signals"]) >= 2:
        assert result["signals"][0].final_score >= result["signals"][1].final_score


def test_score_signal_returns_scored_signal(orchestrator):
    """Test signal scoring logic."""
    from datetime import timedelta
    
    raw_signal = RawSignal(
        source="Test Source",
        title="Test Signal",
        url="https://example.com",
        abstract="Test abstract",
        date=datetime.now(timezone.utc) - timedelta(days=10),  # Recent but not too recent
        raw_score=10.0,
        mission="General",
        metadata={}
    )
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)  # 1 year cutoff
    scored = orchestrator._score_signal(raw_signal, cutoff)
    
    assert scored is not None
    assert hasattr(scored, "final_score")
    assert hasattr(scored, "score_activity")
    assert hasattr(scored, "score_attention")
    assert hasattr(scored, "score_recency")
    assert scored.final_score > 0


def test_score_signal_filters_old_signals(orchestrator):
    """Test that old signals are filtered out."""
    from datetime import timedelta
    
    old_signal = RawSignal(
        source="Test Source",
        title="Old Signal",
        url="https://example.com",
        abstract="Test abstract",
        date=datetime.now(timezone.utc) - timedelta(days=500),  # Very old
        raw_score=10.0,
        mission="General",
        metadata={}
    )
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    scored = orchestrator._score_signal(old_signal, cutoff)
    
    assert scored is None  # Old signal should be filtered


def test_filter_by_threshold(orchestrator):
    """Test filtering signals by threshold."""
    signals = [
        SignalCard(
            title="High Score",
            url="https://example.com/1",
            summary="Test",
            source="Test",
            mission="General",
            date="2024-01-01",
            score_activity=8.0,
            score_attention=9.0,
            score_recency=7.0,
            final_score=8.5,
            typology="Hype"
        ),
        SignalCard(
            title="Low Score",
            url="https://example.com/2",
            summary="Test",
            source="Test",
            mission="General",
            date="2024-01-01",
            score_activity=2.0,
            score_attention=1.0,
            score_recency=3.0,
            final_score=2.0,
            typology="Nascent"
        ),
    ]
    
    filtered = orchestrator._filter_by_threshold(signals, min_score=5.0)
    
    assert len(filtered) == 1
    assert filtered[0].title == "High Score"


def test_sort_by_score(orchestrator):
    """Test sorting signals by score."""
    signals = [
        SignalCard(
            title="Medium",
            url="https://example.com/1",
            summary="Test",
            source="Test",
            mission="General",
            date="2024-01-01",
            score_activity=5.0,
            score_attention=5.0,
            score_recency=5.0,
            final_score=5.0,
            typology="Nascent"
        ),
        SignalCard(
            title="High",
            url="https://example.com/2",
            summary="Test",
            source="Test",
            mission="General",
            date="2024-01-01",
            score_activity=9.0,
            score_attention=9.0,
            score_recency=9.0,
            final_score=9.0,
            typology="Hype"
        ),
        SignalCard(
            title="Low",
            url="https://example.com/3",
            summary="Test",
            source="Test",
            mission="General",
            date="2024-01-01",
            score_activity=2.0,
            score_attention=2.0,
            score_recency=2.0,
            final_score=2.0,
            typology="Nascent"
        ),
    ]
    
    sorted_signals = orchestrator._sort_by_score(signals)
    
    assert sorted_signals[0].title == "High"
    assert sorted_signals[1].title == "Medium"
    assert sorted_signals[2].title == "Low"


def test_classify_source_social(orchestrator):
    """Test source classification for social media."""
    signal = RawSignal(
        source="Reddit",
        title="Test",
        url="https://reddit.com/r/test",
        abstract="Test",
        date=datetime.now(timezone.utc),
        raw_score=0.0,
        mission="General",
        metadata={}
    )
    
    category = orchestrator._classify_source(signal)
    assert category == "social"


def test_classify_source_blog(orchestrator):
    """Test source classification for blogs."""
    signal = RawSignal(
        source="Blog",
        title="Test",
        url="https://medium.com/@author/post",
        abstract="Test",
        date=datetime.now(timezone.utc),
        raw_score=0.0,
        mission="General",
        metadata={}
    )
    
    category = orchestrator._classify_source(signal)
    assert category == "blog"


def test_classify_source_academic(orchestrator):
    """Test source classification for academic sources."""
    signal = RawSignal(
        source="UKRI GtR",
        title="Test",
        url="https://gtr.ukri.org/projects",
        abstract="Test",
        date=datetime.now(timezone.utc),
        raw_score=0.0,
        mission="General",
        metadata={}
    )
    
    category = orchestrator._classify_source(signal)
    assert category == "academic"


def test_classify_source_none_source(orchestrator):
    """Test source classification handles empty/missing source field."""
    signal = RawSignal(
        source="",
        title="Test",
        url="https://reddit.com/r/test",
        abstract="Test",
        date=datetime.now(timezone.utc),
        raw_score=0.0,
        mission="General",
        metadata={}
    )

    category = orchestrator._classify_source(signal)
    assert category == "social"


def test_classify_source_none_url(orchestrator):
    """Test source classification handles empty/missing url field."""
    signal = RawSignal(
        source="GtR Academic",
        title="Test",
        url="",
        abstract="Test",
        date=datetime.now(timezone.utc),
        raw_score=0.0,
        mission="General",
        metadata={}
    )

    category = orchestrator._classify_source(signal)
    assert category == "academic"


def test_classify_source_both_none(orchestrator):
    """Test source classification handles both empty source and url."""
    signal = RawSignal(
        source="",
        title="Test",
        url="",
        abstract="Test",
        date=datetime.now(timezone.utc),
        raw_score=0.0,
        mission="General",
        metadata={}
    )

    category = orchestrator._classify_source(signal)
    assert category == "international"


def test_classify_source_none_safety(orchestrator):
    """Test _classify_source handles None values at runtime without crashing."""
    signal = RawSignal(
        source="Test",
        title="Test",
        url="https://example.com",
        abstract="Test",
        date=datetime.now(timezone.utc),
        raw_score=0.0,
        mission="General",
        metadata={}
    )
    # Simulate runtime None values (e.g. from upstream data bypassing validation)
    signal.source = None  # type: ignore[assignment]
    signal.url = None  # type: ignore[assignment]

    category = orchestrator._classify_source(signal)
    assert category == "international"  # Falls through to default
