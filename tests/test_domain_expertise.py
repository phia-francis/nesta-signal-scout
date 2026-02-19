"""
Tests for upgraded domain expertise in AI system instructions.
"""
from __future__ import annotations

from app.core.prompts import get_system_instructions, SYSTEM_INSTRUCTIONS


def test_system_instructions_defines_weak_signal():
    """Test that prompt defines what a weak signal is (and is not)."""
    for mission in ["Any", "A Healthy Life"]:
        prompt = get_system_instructions(mission)
        assert "Weak Signal" in prompt
        assert "early indicator of change" in prompt
        assert "NOT mainstream news" in prompt


def test_system_instructions_has_scoring_rubric():
    """Test that prompt includes scoring rubric with calibration rules."""
    prompt = get_system_instructions("Any")
    assert "Score_Activity" in prompt
    assert "Score_Attention" in prompt
    assert "Confidence" in prompt
    assert ".gov" in prompt


def test_system_instructions_has_mission_definitions():
    """Test that prompt defines all three Nesta missions with examples."""
    prompt = get_system_instructions("Any")
    assert "Decarbonisation" in prompt
    assert "heat pumps" in prompt
    assert "obesity" in prompt.lower()
    assert "Early years education" in prompt


def test_system_instructions_enforces_british_english():
    """Test that rules explicitly mandate British English spelling."""
    prompt = get_system_instructions("Any")
    assert "British English" in prompt
    assert "decarbonisation" in prompt


def test_system_instructions_constant_matches_function():
    """Test that SYSTEM_INSTRUCTIONS constant has matching domain expertise."""
    assert "Nesta Signal Scout" in SYSTEM_INSTRUCTIONS
    assert "Weak Signal" in SYSTEM_INSTRUCTIONS
    assert "Score_Activity" in SYSTEM_INSTRUCTIONS
    assert "Score_Attention" in SYSTEM_INSTRUCTIONS
    assert "Decarbonisation" in SYSTEM_INSTRUCTIONS
    assert "British English" in SYSTEM_INSTRUCTIONS
