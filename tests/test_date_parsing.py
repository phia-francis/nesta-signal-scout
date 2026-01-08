from datetime import datetime
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from main import parse_source_date, is_date_within_time_filter


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2024-03-10", datetime(2024, 3, 10)),
        ("2024/03/10", datetime(2024, 3, 10)),
        ("10/03/2024", datetime(2024, 3, 10)),
        ("10-03-2024", datetime(2024, 3, 10)),
        ("March 10, 2024", datetime(2024, 3, 10)),
        ("Mar 10, 2024", datetime(2024, 3, 10)),
        ("10 March 2024", datetime(2024, 3, 10)),
        ("10 Mar 2024", datetime(2024, 3, 10)),
        ("March 2024", datetime(2024, 3, 1)),
        ("Mar 2024", datetime(2024, 3, 1)),
        ("2024", datetime(2024, 1, 1)),
        ("Published | 2024-03-10 • Update", datetime(2024, 3, 10)),
        ("Updated on 10/03/2024", datetime(2024, 3, 10)),
    ],
)
def test_parse_source_date_supported_formats(raw, expected):
    assert parse_source_date(raw) == expected


@pytest.mark.parametrize("raw", ["", "recent", "unknown", "n/a", "NA", "TBD", "yesterday"])
def test_parse_source_date_invalid_or_placeholder(raw):
    assert parse_source_date(raw) is None


def test_parse_source_date_unparseable_text():
    assert parse_source_date("not a date here") is None


def test_is_date_within_time_filter_month_boundary():
    request_date = datetime(2024, 3, 15)
    assert is_date_within_time_filter("2024-02-15", "Past Month", request_date) is True
    assert is_date_within_time_filter("2024-02-14", "Past Month", request_date) is False
