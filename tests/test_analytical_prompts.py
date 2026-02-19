"""
Tests for anti-copy-paste analytical prompt requirements.
"""
from __future__ import annotations

from app.core.prompts import build_analysis_prompt, get_system_instructions


def test_system_instructions_forbid_copy_paste():
    """Test that system instructions explicitly forbid copy-pasting."""
    for mission in ["Any", "A Healthy Life", "A Sustainable Future", "A Fairer Start"]:
        prompt = get_system_instructions(mission)
        assert "DO NOT copy-paste" in prompt
        assert "So What?" in prompt


def test_system_instructions_require_implications():
    """Test that system instructions demand analysis of implications."""
    prompt = get_system_instructions("Any")
    assert "implications" in prompt
    assert "drivers" in prompt


def test_analysis_prompt_defines_signal_schema():
    """Test that analysis prompt defines required signal object fields."""
    prompt = build_analysis_prompt("test query", "test context")
    assert '"title"' in prompt
    assert '"summary"' in prompt
    assert '"source"' in prompt


def test_analysis_prompt_requires_analytical_summary():
    """Test that analysis prompt demands analytical not descriptive summaries."""
    prompt = build_analysis_prompt("test query", "test context")
    assert "DO NOT copy-paste" in prompt
    assert "core innovation" in prompt
    assert "underlying drivers" in prompt
    assert "strategic implications" in prompt


def test_analysis_prompt_includes_query_and_context():
    """Test that query and context are inserted into the prompt."""
    prompt = build_analysis_prompt("heat pumps UK", "Source: gov.uk subsidy data")
    assert "heat pumps UK" in prompt
    assert "Source: gov.uk subsidy data" in prompt
