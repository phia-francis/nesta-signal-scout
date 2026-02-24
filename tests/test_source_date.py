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


def test_add_signals_to_sheet_uses_append_rows():
    """Test that add_signals_to_sheet delegates to worksheet.append_rows."""
    settings = Mock()
    settings.GOOGLE_CREDENTIALS = '{"type":"service_account","project_id":"x","private_key_id":"x","private_key":"-----BEGIN RSA PRIVATE KEY-----\\nMIIBogIBAAJBALRiMLAH...\\n-----END RSA PRIVATE KEY-----\\n","client_email":"x@x.iam.gserviceaccount.com","client_id":"1","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token"}'
    settings.SHEET_ID = "test-sheet-id"

    svc = _make_sheet_service()

    mock_worksheet = Mock()
    mock_spreadsheet = Mock()
    mock_spreadsheet.worksheet.return_value = mock_worksheet

    svc._open_spreadsheet = Mock(return_value=mock_spreadsheet)

    signals = [
        {"Title": "Signal A", "Score": 85, "Hook": "Hook A", "URL": "https://example.com/a",
         "Mission": "A Healthy Life", "Origin_Country": "UK", "Lenses": "Tech",
         "Score_Impact": "8", "Score_Novelty": "7", "Score_Evidence": "9"},
        {"Title": "Signal B", "Score": 70, "Hook": "Hook B", "URL": "https://example.com/b",
         "Mission": "A Fairer Start"},
    ]

    svc.add_signals_to_sheet(signals)

    mock_worksheet.append_rows.assert_called_once()
    rows = mock_worksheet.append_rows.call_args[0][0]
    assert len(rows) == 2
    assert rows[0][0] == "Signal A"
    assert rows[0][1] == 85
    assert rows[1][0] == "Signal B"
    # Verify value_input_option is passed
    assert mock_worksheet.append_rows.call_args[1]["value_input_option"] == "USER_ENTERED"


def test_add_signals_to_sheet_empty_list():
    """Test that add_signals_to_sheet does nothing with empty list."""
    svc = _make_sheet_service()

    mock_worksheet = Mock()
    mock_spreadsheet = Mock()
    mock_spreadsheet.worksheet.return_value = mock_worksheet

    svc._open_spreadsheet = Mock(return_value=mock_spreadsheet)

    svc.add_signals_to_sheet([])

    mock_worksheet.append_rows.assert_not_called()
