"""
Tests for source publication date in sheet service row mapping.
"""
from __future__ import annotations

from unittest.mock import Mock

from app.services.sheet_svc import SheetService


def _make_sheet_service() -> SheetService:
    """Create a SheetService with no real Google credentials."""
    settings = Mock()
    settings.GOOGLE_CREDENTIALS = None
    settings.SHEET_ID = None
    return SheetService(settings=settings)


def test_signal_to_row_includes_source_date():
    """Test that _signal_to_row includes the date field as the 13th element."""
    svc = _make_sheet_service()
    signal = {
        "mode": "Radar",
        "mission": "A Healthy Life",
        "title": "Test Signal",
        "url": "https://example.com",
        "summary": "A summary.",
        "typology": "Trend",
        "score_activity": 8.0,
        "score_attention": 7.0,
        "source": "Web",
        "status": "New",
        "narrative_group": "",
        "source_date": "2025-11-15",
    }
    row = svc._signal_to_row(signal)

    assert len(row) == 13
    assert row[12] == "2025-11-15"


def test_signal_to_row_defaults_date_to_unknown():
    """Test that _signal_to_row defaults date to 'Unknown' when missing."""
    svc = _make_sheet_service()
    signal = {"title": "No Date Signal"}
    row = svc._signal_to_row(signal)

    assert len(row) == 13
    assert row[12] == "Unknown"


def test_source_date_column_index():
    """Test that SOURCE_DATE_COLUMN_INDEX is 13 (Column M)."""
    assert SheetService.SOURCE_DATE_COLUMN_INDEX == 13
