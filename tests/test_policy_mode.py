"""
Tests for policy mode improvements: modifiers, prompt, and search.
"""
from __future__ import annotations

import keywords
from app.core.prompts import POLICY_SYSTEM_PROMPT


def test_get_policy_modifiers_returns_list():
    """Test that get_policy_modifiers returns a list of modifier strings."""
    modifiers = keywords.get_policy_modifiers("building regulations")
    assert isinstance(modifiers, list)
    assert len(modifiers) > 0
    assert all(isinstance(m, str) for m in modifiers)


def test_get_policy_modifiers_returns_top_five():
    """Test that get_policy_modifiers returns exactly 5 modifiers."""
    modifiers = keywords.get_policy_modifiers("tax credits")
    assert len(modifiers) == 5


def test_policy_modifiers_constant_exists():
    """Test that POLICY_MODIFIERS constant is defined."""
    assert hasattr(keywords, "POLICY_MODIFIERS")
    assert isinstance(keywords.POLICY_MODIFIERS, list)
    assert len(keywords.POLICY_MODIFIERS) > 0


def test_policy_modifiers_contain_regulatory_terms():
    """Test that policy modifiers include regulatory terms."""
    modifiers = keywords.get_policy_modifiers("energy")
    assert any(term in modifiers for term in ["legislation", "regulation", "mandate"])


def test_policy_system_prompt_contains_authority_boost():
    """Test that POLICY_SYSTEM_PROMPT includes authority boost for gov sources."""
    assert ".gov" in POLICY_SYSTEM_PROMPT
    assert ".gov.uk" in POLICY_SYSTEM_PROMPT
    assert "7.5" in POLICY_SYSTEM_PROMPT


def test_policy_system_prompt_penalises_wikipedia():
    """Test that POLICY_SYSTEM_PROMPT penalises encyclopedic content."""
    assert "Wikipedia" in POLICY_SYSTEM_PROMPT
    assert "Score < 3.0" in POLICY_SYSTEM_PROMPT


def test_policy_system_prompt_uses_british_english():
    """Test that POLICY_SYSTEM_PROMPT uses British English."""
    assert "Penalise" in POLICY_SYSTEM_PROMPT or "Recognised" in POLICY_SYSTEM_PROMPT
