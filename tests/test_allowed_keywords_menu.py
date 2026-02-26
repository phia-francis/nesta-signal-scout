import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.api.routes import radar as main


def _set_keywords(monkeypatch, missions, cross_cutting):
    monkeypatch.setattr(main, "MISSION_KEYWORDS", missions, raising=False)
    monkeypatch.setattr(main, "CROSS_CUTTING_KEYWORDS", cross_cutting, raising=False)
    main.build_allowed_keywords_menu.cache_clear()


def test_build_allowed_keywords_menu_with_mission_and_cross_cutting(monkeypatch):
    _set_keywords(monkeypatch, {"Mission A": ["alpha"]}, ["cross"])

    menu = main.build_allowed_keywords_menu("All Missions")

    assert "- Mission A: alpha" in menu
    assert "- Cross-cutting: cross" in menu


def test_build_allowed_keywords_menu_with_only_mission(monkeypatch):
    _set_keywords(monkeypatch, {"Mission A": ["alpha"]}, [])

    menu = main.build_allowed_keywords_menu("All Missions")

    assert "- Mission A: alpha" in menu
    assert "Cross-cutting" not in menu


def test_build_allowed_keywords_menu_with_empty_sources(monkeypatch):
    _set_keywords(monkeypatch, {}, [])

    menu = main.build_allowed_keywords_menu("All Missions")

    assert menu == "Error: Could not load keywords.py variables."


def test_build_allowed_keywords_menu_ignores_empty_mission_terms(monkeypatch):
    _set_keywords(monkeypatch, {"Mission A": []}, [])

    menu = main.build_allowed_keywords_menu("Mission A")

    assert menu == "Error: Could not load keywords.py variables."


def test_build_allowed_keywords_menu_filters_by_mission(monkeypatch):
    _set_keywords(
        monkeypatch,
        {"Mission A": ["alpha"], "Mission B": ["bravo"]},
        ["cross"],
    )

    menu = main.build_allowed_keywords_menu("Mission A")

    assert "- Mission A: alpha" in menu
    assert "- Mission B: bravo" not in menu
