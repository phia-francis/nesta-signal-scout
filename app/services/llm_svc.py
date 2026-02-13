from __future__ import annotations

from typing import Any

SUMMARY_SOURCE_LINE_LIMIT = 10
SUMMARY_MAX_LENGTH = 500


class LLMService:
    """Lightweight synthesis service for signal generation."""

    async def generate_signal(self, context: str, system_prompt: str, mode: str) -> dict[str, Any]:
        del system_prompt
        lines = [line.strip() for line in context.splitlines() if line.strip()]
        summary = (
            " ".join(lines[:SUMMARY_SOURCE_LINE_LIMIT])[:SUMMARY_MAX_LENGTH]
            if lines
            else "No synthesis context available."
        )
        return {
            "title": "Research Synthesis",
            "summary": summary,
            "source": "Web Synthesis",
            "mission": mode,
            "typology": "Synthesis",
            "score_activity": 0,
            "score_attention": 0,
            "mode": mode,
        }
