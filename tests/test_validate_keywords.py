import keywords
from scripts import validate_keywords as vk


def test_validate_keywords_missing_mission_keywords(monkeypatch):
    monkeypatch.delattr(keywords, "MISSION_KEYWORDS", raising=False)
    monkeypatch.setattr(keywords, "CROSS_CUTTING_KEYWORDS", ["cross"], raising=False)

    errors = vk.validate_keywords()

    assert any("Missing MISSION_KEYWORDS" in error for error in errors)


def test_validate_keywords_detects_invalid_types(monkeypatch):
    monkeypatch.setattr(keywords, "MISSION_KEYWORDS", ["not-a-dict"], raising=False)
    monkeypatch.setattr(keywords, "CROSS_CUTTING_KEYWORDS", "not-a-list", raising=False)

    errors = vk.validate_keywords()

    assert "MISSION_KEYWORDS must be a dict." in errors
    assert "CROSS_CUTTING_KEYWORDS must be a list." in errors


def test_validate_keywords_detects_duplicates_and_empty_terms(monkeypatch):
    monkeypatch.setattr(
        keywords,
        "MISSION_KEYWORDS",
        {"Mission A": ["alpha", "alpha", ""]},
        raising=False,
    )
    monkeypatch.setattr(keywords, "CROSS_CUTTING_KEYWORDS", ["cross"], raising=False)

    errors = vk.validate_keywords()

    assert any("duplicate value" in error for error in errors)
    assert any("empty/blank string" in error for error in errors)


def test_validate_keywords_detects_missing_cross_cutting(monkeypatch):
    monkeypatch.setattr(keywords, "MISSION_KEYWORDS", {"Mission A": ["alpha"]}, raising=False)
    monkeypatch.delattr(keywords, "CROSS_CUTTING_KEYWORDS", raising=False)

    errors = vk.validate_keywords()

    assert any("Missing CROSS_CUTTING_KEYWORDS" in error for error in errors)
