"""
Production LLM service with real OpenAI integration for signal synthesis.
"""
from __future__ import annotations

import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    OpenAI-powered synthesis service for research and intelligence modes.
    Generates comprehensive signal cards from multiple sources.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS

    async def generate_signal(self, context: str, system_prompt: str, mode: str) -> dict[str, Any]:
        """
        Generate a single synthesised Signal Card from aggregated context.

        Args:
            context: Aggregated text from multiple sources (snippets, abstracts, etc.)
            system_prompt: Instructions for the LLM on how to synthesise
            mode: Scan mode (Research, Intelligence, etc.) for metadata

        Returns:
            Dictionary with Signal Card fields
        """
        try:
            # Construct user message with context
            user_message = f"""Based on the following aggregated sources, create a comprehensive signal card.

SOURCES:
{context}

Your response must be a JSON object with these fields:
- title: A clear, descriptive headline (max 120 characters)
- summary: A comprehensive synthesis of all sources, highlighting key insights, conflicts, and trends (400-600 characters)
- mission: "{mode}"
- typology: One of: "Nascent", "Hidden Gem", "Hype", or "Established"
- score_activity: Estimated research/funding activity (0-10 scale, based on source credibility)
- score_attention: Estimated public/media attention (0-10 scale, based on source diversity)

Remember:
- Synthesise, don't just summarise one source
- Highlight emerging patterns and tensions
- Be specific about what makes this signal noteworthy
- Use clear, accessible language for policy audience"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=self.max_tokens,
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            # Parse response
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")

            import json

            synthesis = json.loads(content)

            # Ensure all required fields are present with defaults
            return {
                "title": synthesis.get("title", "Research Synthesis")[:120],
                "summary": synthesis.get("summary", "Synthesis unavailable")[:600],
                "source": "AI Synthesis",
                "mission": synthesis.get("mission", mode),
                "typology": synthesis.get("typology", "Nascent"),
                "score_activity": max(0, min(10, float(synthesis.get("score_activity", 5)))),
                "score_attention": max(0, min(10, float(synthesis.get("score_attention", 5)))),
                "mode": mode,
            }

        except Exception as e:
            logger.error("LLM synthesis failed: %s", e, exc_info=True)
            # Fallback: return a basic card with raw context snippet
            lines = [line.strip() for line in context.splitlines() if line.strip()]
            fallback_summary = " ".join(lines[:10])[:500] if lines else "Synthesis unavailable due to processing error."

            return {
                "title": "Research Synthesis (Fallback)",
                "summary": fallback_summary,
                "source": "Aggregated Sources",
                "mission": mode,
                "typology": "Nascent",
                "score_activity": 0,
                "score_attention": 0,
                "mode": mode,
            }

    async def process_single_result(self, result: dict[str, Any], mode: str) -> dict[str, Any] | None:
        """
        Convert a single search result into a Signal Card (for Radar/Policy modes).
        No LLM synthesis needed - just format the result.
        """
        url = str(result.get("url") or result.get("link") or "").strip()
        if not url:
            return None

        return {
            "title": (result.get("title") or "Untitled")[:120],
            "url": url,
            "summary": (result.get("snippet") or result.get("summary") or "")[:500],
            "source": result.get("source", "Web"),
            "mission": result.get("mission", "General"),
            "typology": result.get("typology", "Nascent"),
            "score_activity": float(result.get("score_activity", 0)),
            "score_attention": float(result.get("score_attention", 0)),
            "mode": mode,
        }
