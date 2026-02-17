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
    
    return {
        "gateway": gateway_service,
        "openalex": openalex_service,
        "search": search_service,
        "analytics": analytics_service,
        "taxonomy": taxonomy
    }


@pytest.fixture
def orchestrator(mock_services):
    """Create ScanOrchestrator with mocked services."""
    return ScanOrchestrator(
        gateway_service=mock_services["gateway"],
        openalex_service=mock_services["openalex"],
        search_service=mock_services["search"],
        analytics_service=mock_services["analytics"],
        taxonomy=mock_services["taxonomy"]
    )


@pytest.mark.asyncio
async def test_execute_quick_scan_returns_signals(orchestrator, mock_services):
    """Test that quick scan returns signals with proper structure."""
    # Mock keyword generation
    with patch('keywords.generate_broad_scan_queries', return_value=["term1", "term2"]):
        result = await orchestrator._execute_quick_scan("AI innovation", "A Healthy Life")
    
    assert "signals" in result
    assert "warnings" in result
    assert "mode" in result
    assert result["mode"] == "quick"
    assert isinstance(result["signals"], list)


@pytest.mark.asyncio
async def test_execute_deep_scan_mode(orchestrator):
    """Test deep scan execution."""
    # Mock fetch_research_deep_dive method
    orchestrator.fetch_research_deep_dive = AsyncMock(return_value=[])
    
    result = await orchestrator._execute_deep_scan("quantum computing", "A Sustainable Future")
    
    assert result["mode"] == "deep"
    assert "signals" in result
    assert orchestrator.fetch_research_deep_dive.called


@pytest.mark.asyncio
async def test_execute_monitor_scan_mode(orchestrator):
    """Test monitor scan execution."""
    # Mock fetch_policy_scan method
    orchestrator.fetch_policy_scan = AsyncMock(return_value=[])
    
    result = await orchestrator._execute_monitor_scan("climate policy", "A Sustainable Future")
    
    assert result["mode"] == "monitor"
    assert "signals" in result
    assert orchestrator.fetch_policy_scan.called


@pytest.mark.asyncio
async def test_partial_failure_google_fails_openalex_works(orchestrator, mock_services):
    """Test partial failure: Google fails but other sources work."""
    # Make Google search fail but GtR succeed
    mock_services["search"].search = AsyncMock(side_effect=Exception("Google API error"))
    mock_services["gateway"].fetch_projects = AsyncMock(return_value=[
        {
            "title": "Academic Project",
            "grantReference": "ABC123",
            "abstract": "Test abstract",
            "start_date": datetime.now(timezone.utc),
            "fund_val": 100000
        }
    ])
    
    with patch('keywords.generate_broad_scan_queries', return_value=["term1"]):
        result = await orchestrator._execute_quick_scan("test query", "General")
    
    # Should have warnings but still return results
    assert result["warnings"] is not None
    assert len(result["warnings"]) > 0
    assert any("unavailable" in w.lower() for w in result["warnings"])
    # Should still have academic signals
    assert len(result["signals"]) > 0


@pytest.mark.asyncio
async def test_all_sources_fail_returns_empty(orchestrator, mock_services):
    """Test that when all sources fail, empty results are returned."""
    # Make all sources fail
    mock_services["search"].search = AsyncMock(side_effect=Exception("API error"))
    mock_services["gateway"].fetch_projects = AsyncMock(side_effect=Exception("GtR error"))
    
    with patch('keywords.generate_broad_scan_queries', return_value=[]):
        result = await orchestrator._execute_quick_scan("test query", "General")
    
    assert result["warnings"] is not None
    assert len(result["warnings"]) > 0
    assert len(result["signals"]) == 0


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
