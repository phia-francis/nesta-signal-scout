"""Tests for scan storage layer."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.storage.scan_storage import ScanStorage


@pytest.fixture
def storage():
    """Create a temporary storage instance for testing (local files only)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield ScanStorage(storage_dir=Path(tmpdir))


def test_save_and_retrieve_scan(storage):
    """Test saving and retrieving a scan."""
    query = "climate tech innovation"
    mode = "radar"
    signals = [
        {"title": "Signal 1", "score": 8.5},
        {"title": "Signal 2", "score": 7.2},
    ]
    themes = [
        {"name": "Climate Tech", "signal_ids": [0, 1], "relevance_score": 9.0}
    ]
    warnings = ["Google API unavailable"]
    
    # Save scan
    scan_id = storage.save_scan(
        query=query,
        mode=mode,
        signals=signals,
        themes=themes,
        warnings=warnings
    )
    
    assert scan_id is not None
    assert len(scan_id) > 0
    
    # Retrieve scan
    scan_data = storage.get_scan(scan_id)
    
    assert scan_data is not None
    assert scan_data["scan_id"] == scan_id
    assert scan_data["query"] == query
    assert scan_data["mode"] == mode
    assert len(scan_data["signals"]) == 2
    assert len(scan_data["themes"]) == 1
    assert len(scan_data["warnings"]) == 1
    assert scan_data["signal_count"] == 2


def test_retrieve_nonexistent_scan(storage):
    """Test retrieving a scan that doesn't exist."""
    scan_data = storage.get_scan("nonexistent-uuid")
    assert scan_data is None


def test_update_themes(storage):
    """Test updating themes for an existing scan."""
    query = "AI policy"
    mode = "deep"
    signals = [{"title": "Signal 1", "score": 8.0}]
    
    # Save scan without themes
    scan_id = storage.save_scan(query=query, mode=mode, signals=signals)
    
    # Update themes
    new_themes = [
        {"name": "AI Regulation", "signal_ids": [0], "relevance_score": 8.5}
    ]
    success = storage.update_themes(scan_id, new_themes)
    
    assert success is True
    
    # Verify themes were updated
    scan_data = storage.get_scan(scan_id)
    assert len(scan_data["themes"]) == 1
    assert scan_data["themes"][0]["name"] == "AI Regulation"
    assert "themes_updated_at" in scan_data


def test_update_themes_nonexistent_scan(storage):
    """Test updating themes for a scan that doesn't exist."""
    themes = [{"name": "Test", "signal_ids": [], "relevance_score": 0}]
    success = storage.update_themes("nonexistent-uuid", themes)
    assert success is False


def test_list_scans(storage):
    """Test listing scans."""
    # Create multiple scans
    for i in range(5):
        storage.save_scan(
            query=f"query {i}",
            mode="radar",
            signals=[{"title": f"Signal {i}"}],
            themes=[{"name": f"Theme {i}", "signal_ids": [0], "relevance_score": 7.0}]
        )
    
    # List scans
    scans = storage.list_scans(limit=10)
    
    assert len(scans) == 5
    assert all("scan_id" in scan for scan in scans)
    assert all("query" in scan for scan in scans)
    assert all("signal_count" in scan for scan in scans)
    assert all("theme_count" in scan for scan in scans)
    
    # Verify metadata
    assert scans[0]["theme_count"] == 1
    assert scans[0]["signal_count"] == 1


def test_list_scans_with_limit(storage):
    """Test listing scans with limit."""
    # Create 10 scans
    for i in range(10):
        storage.save_scan(
            query=f"query {i}",
            mode="radar",
            signals=[{"title": f"Signal {i}"}]
        )
    
    # List with limit of 5
    scans = storage.list_scans(limit=5)
    assert len(scans) == 5


def test_delete_scan(storage):
    """Test deleting a scan."""
    query = "test deletion"
    mode = "radar"
    signals = [{"title": "Signal 1"}]
    
    # Save scan
    scan_id = storage.save_scan(query=query, mode=mode, signals=signals)
    
    # Verify it exists
    assert storage.get_scan(scan_id) is not None
    
    # Delete scan
    success = storage.delete_scan(scan_id)
    assert success is True
    
    # Verify it's gone
    assert storage.get_scan(scan_id) is None


def test_delete_nonexistent_scan(storage):
    """Test deleting a scan that doesn't exist."""
    success = storage.delete_scan("nonexistent-uuid")
    assert success is False


def test_cleanup_old_scans(storage):
    """Test cleanup of old scans."""
    # Create an old scan by manually setting created_at
    old_date = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
    scan_id = storage.save_scan(
        query="old query",
        mode="radar",
        signals=[{"title": "Old signal"}]
    )
    
    # Manually update the created_at date
    scan_file = storage.storage_dir / f"{scan_id}.json"
    with open(scan_file, 'r') as f:
        scan_data = json.load(f)
    scan_data["created_at"] = old_date
    with open(scan_file, 'w') as f:
        json.dump(scan_data, f)
    
    # Create a recent scan
    recent_id = storage.save_scan(
        query="recent query",
        mode="radar",
        signals=[{"title": "Recent signal"}]
    )
    
    # Run cleanup (30 days retention)
    deleted_count = storage.cleanup_old_scans(days=30)
    
    assert deleted_count == 1
    assert storage.get_scan(scan_id) is None
    assert storage.get_scan(recent_id) is not None


def test_empty_storage(storage):
    """Test operations on empty storage."""
    scans = storage.list_scans()
    assert len(scans) == 0
    
    deleted_count = storage.cleanup_old_scans()
    assert deleted_count == 0


def test_concurrent_save(storage):
    """Test concurrent save operations."""
    # Save multiple scans to test file locking
    scan_ids = []
    for i in range(10):
        scan_id = storage.save_scan(
            query=f"concurrent query {i}",
            mode="radar",
            signals=[{"title": f"Signal {i}"}]
        )
        scan_ids.append(scan_id)
    
    # Verify all were saved
    assert len(scan_ids) == 10
    assert len(set(scan_ids)) == 10  # All unique
    
    # Verify all can be retrieved
    for scan_id in scan_ids:
        scan_data = storage.get_scan(scan_id)
        assert scan_data is not None


# ---- Google Sheets integration tests (mocked) ----

@pytest.fixture
def mock_worksheet():
    """Create a mock Google Sheets worksheet."""
    ws = MagicMock()
    ws.append_row = MagicMock()
    ws.col_values = MagicMock(return_value=["scan_id"])  # header only
    ws.row_values = MagicMock(return_value=[])
    return ws


@pytest.fixture
def mock_sheets_client(mock_worksheet):
    """Create a mock gspread client."""
    client = MagicMock()
    spreadsheet = MagicMock()
    spreadsheet.worksheet.return_value = mock_worksheet
    client.open_by_key.return_value = spreadsheet
    return client


@pytest.fixture
def sheets_storage(mock_sheets_client):
    """Create a ScanStorage instance with mocked Google Sheets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield ScanStorage(
            storage_dir=Path(tmpdir),
            sheets_client=mock_sheets_client,
            spreadsheet_id="test-spreadsheet-id",
        )


def test_save_scan_writes_to_sheets(sheets_storage, mock_worksheet):
    """Test that save_scan writes to both local file and Google Sheets."""
    scan_id = sheets_storage.save_scan(
        query="test query",
        mode="radar",
        signals=[{"title": "Signal 1"}],
    )

    assert scan_id is not None
    # Verify Google Sheets was called
    mock_worksheet.append_row.assert_called_once()
    row = mock_worksheet.append_row.call_args[0][0]
    assert row[0] == scan_id
    assert row[2] == "test query"
    assert row[3] == "radar"
    # Payload is JSON in column 5
    payload = json.loads(row[4])
    assert payload["query"] == "test query"
    assert len(payload["signals"]) == 1


def test_get_scan_falls_back_to_sheets(sheets_storage, mock_worksheet):
    """Test that get_scan falls back to Google Sheets when local file missing."""
    scan_data = {
        "scan_id": "sheets-only-id",
        "query": "persisted query",
        "mode": "radar",
        "signals": [{"title": "Persisted Signal"}],
        "themes": [],
    }
    # Mock Sheets returning the scan via col_values batch lookup
    mock_worksheet.col_values.return_value = ["scan_id", "sheets-only-id"]
    mock_worksheet.row_values.return_value = [
        "sheets-only-id",
        "2025-02-19 14:30:00",
        "persisted query",
        "radar",
        json.dumps(scan_data),
    ]

    result = sheets_storage.get_scan("sheets-only-id")

    assert result is not None
    assert result["query"] == "persisted query"
    assert result["scan_id"] == "sheets-only-id"
    mock_worksheet.col_values.assert_called_with(1)


def test_get_scan_prefers_local_cache(sheets_storage, mock_worksheet):
    """Test that get_scan uses local file when available, not Sheets."""
    # Save locally first
    scan_id = sheets_storage.save_scan(
        query="local query",
        mode="radar",
        signals=[{"title": "Local Signal"}],
    )

    # Reset Sheets mock call counts
    mock_worksheet.col_values.reset_mock()

    # Retrieve - should use local file, not Sheets
    result = sheets_storage.get_scan(scan_id)
    assert result is not None
    assert result["query"] == "local query"
    # Sheets col_values should NOT have been called since local file exists
    mock_worksheet.col_values.assert_not_called()


def test_get_scan_recaches_from_sheets(sheets_storage, mock_worksheet):
    """Test that scan retrieved from Sheets is re-cached locally."""
    scan_data = {
        "scan_id": "recache-test",
        "query": "recache query",
        "mode": "radar",
        "signals": [],
        "themes": [],
    }
    mock_worksheet.col_values.return_value = ["scan_id", "recache-test"]
    mock_worksheet.row_values.return_value = [
        "recache-test", "2025-02-19", "recache query", "radar",
        json.dumps(scan_data),
    ]

    # First retrieval - should hit Sheets
    result = sheets_storage.get_scan("recache-test")
    assert result is not None
    mock_worksheet.col_values.assert_called_once()

    # Reset and retrieve again - should use local cache now
    mock_worksheet.col_values.reset_mock()
    result = sheets_storage.get_scan("recache-test")
    assert result is not None
    mock_worksheet.col_values.assert_not_called()


def test_sheets_unavailable_falls_back_to_local(mock_worksheet):
    """Test that storage works with local files when Sheets is unavailable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = ScanStorage(storage_dir=Path(tmpdir))

        scan_id = storage.save_scan(
            query="offline query",
            mode="radar",
            signals=[{"title": "Offline Signal"}],
        )

        result = storage.get_scan(scan_id)
        assert result is not None
        assert result["query"] == "offline query"


def test_sheets_error_does_not_break_save(mock_worksheet):
    """Test that Sheets errors don't prevent local save."""
    client = MagicMock()
    client.open_by_key.side_effect = Exception("Sheets API error")

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = ScanStorage(
            storage_dir=Path(tmpdir),
            sheets_client=client,
            spreadsheet_id="test-id",
        )

        # Save should succeed (local file) even though Sheets fails
        scan_id = storage.save_scan(
            query="resilient query",
            mode="radar",
            signals=[{"title": "Signal"}],
        )

        assert scan_id is not None
        result = storage.get_scan(scan_id)
        assert result is not None
        assert result["query"] == "resilient query"
