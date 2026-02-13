from __future__ import annotations

from typing import Any


class LLMService:
    """Lightweight synthesis service for signal generation."""

    async def generate_signal(self, context: str, system_prompt: str, mode: str) -> dict[str, Any]:
        del system_prompt
        lines = [line.strip() for line in context.splitlines() if line.strip()]
        summary = " ".join(lines[:10])[:500] if lines else "No synthesis context available."
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
