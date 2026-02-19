from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.exceptions import LLMServiceError
from app.core.prompts import (
    SYSTEM_INSTRUCTIONS, 
    build_analysis_prompt,
    CLUSTERING_INSTRUCTIONS,
    build_clustering_prompt,
    get_system_instructions,
)

logger = logging.getLogger(__name__)


class LLMService:
    """
    OpenAI LLM integration for signal synthesis and clustering.

    Provides stateless AI analysis of search results, including theme
    extraction and narrative synthesis. Each call includes full context
    as the service maintains no conversation history.
    """

    def __init__(self, settings: Any = None) -> None:
        """
        Initialise the LLM service.

        Args:
            settings: Application settings containing the OpenAI API key
                      and model configuration. Falls back to global settings
                      if not provided.
        """
        self.settings = settings or get_settings()
        # Only initialize OpenAI client if API key is available
        if self.settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
        else:
            self.client = None
            logger.warning("LLMService initialized without OPENAI_API_KEY. Synthesis will not be available.")
        self.model = self.settings.CHAT_MODEL

    async def synthesize_research(self, query: str, search_results: list[dict[str, Any]], mission: str = "Any") -> dict[str, Any]:
        """
        Synthesise raw search results into a structured research summary.

        Takes raw search results, formats them into a context window, and
        calls the LLM to produce a JSON synthesis with extracted signals.
        The system prompt adapts dynamically based on the selected mission.

        Args:
            query: The research query or topic to synthesise around.
            search_results: List of search result dictionaries, each
                            containing at least 'title' and 'snippet' keys.
            mission: Nesta mission for focused analysis (default ``"Any"``
                     for cross-cutting mode).

        Returns:
            Dictionary with:
                - synthesis: Narrative summary text
                - signals: List of extracted signal objects

        Raises:
            LLMServiceError: If the OpenAI API call fails.
        """
        # Check if OpenAI client is available
        if not self.client:
            logger.warning("OpenAI client not initialized. Returning fallback response.")
            return {"synthesis": "LLM synthesis unavailable - OpenAI API key not configured.", "signals": []}
        
        # 1. Build the Context Window (The "Memory" for this single turn)
        context_str = self._format_results_for_llm(search_results)
        
        if not context_str:
            return {"synthesis": "No data found to analyse.", "signals": []}

        # 2. Construct Messages (System + User w/ Context)
        system_prompt = get_system_instructions(mission)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_analysis_prompt(query, context_str)}
        ]

        try:
            # 3. Call OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,  # Low temperature for factual grounding
            )
            
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
            else:
                return {"synthesis": "No response generated.", "signals": []}

        except Exception as e:
            logger.error(f"LLM Synthesis failed: {e}", exc_info=True)
            raise LLMServiceError(
                f"LLM synthesis failed: {str(e)}",
                model=self.model,
            ) from e

    def _format_results_for_llm(self, results: list[dict[str, Any]]) -> str:
        """
        Convert search result dictionaries into a dense text block for the AI.

        Formats up to 15 results into numbered entries containing title,
        source, and snippet for token-efficient context injection.

        Args:
            results: List of search result dictionaries, each containing
                     'title', 'snippet'/'abstract', and 'displayLink'/'source'.

        Returns:
            Formatted string with numbered results separated by blank lines.
        """
        buffer = []
        for i, item in enumerate(results[:15], 1):  # Limit to top 15 to save tokens
            title = item.get("title", "Unknown")
            snippet = item.get("snippet", item.get("abstract", "No summary"))
            source = item.get("displayLink", item.get("source", "Unknown Source"))
            buffer.append(f"[{i}] {title} ({source}): {snippet}")
        return "\n\n".join(buffer)

    async def generate_signal(self, context: str, system_prompt: str, mode: str) -> dict[str, Any]:
        """
        Generate an AI-synthesised signal card from raw context.

        Args:
            context: Concatenated search snippets / source text.
            system_prompt: System instructions for synthesis behaviour.
            mode: Operating mode label (e.g. ``"Research"``).

        Returns:
            Dictionary representing a signal card with title, summary,
            source, mission, typology, scores, and mode.

        Raises:
            ValueError: If *context* is empty.
            LLMServiceError: If the OpenAI API call fails.
        """
        if not self.client:
            logger.warning(
                "OpenAI client not initialized in generate_signal; "
                "returning fallback response instead of calling the API."
            )
            return {
                "title": "Research Synthesis",
                "summary": "LLM client is not configured; unable to generate AI-driven synthesis.",
                "source": "Web Synthesis",
                "mission": "Research",
                "typology": "Synthesis",
                "score_activity": 0,
                "score_attention": 0,
                "final_score": 0,
                "mode": mode.title(),
            }

        if not context or not context.strip():
            raise ValueError("Cannot generate signal from empty context")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context},
                ],
                temperature=0.3,
            )
            summary = (response.choices[0].message.content or "")[:500]
        except Exception as e:
            logger.error("OpenAI API call failed in generate_signal: %s", e, exc_info=True)
            raise LLMServiceError(
                f"LLM generate_signal failed: {str(e)}",
                model=self.model,
            ) from e

        return {
            "title": "Research Synthesis",
            "summary": summary,
            "source": "Web Synthesis",
            "mission": "Research",
            "typology": "Synthesis",
            "score_activity": 0,
            "score_attention": 0,
            "final_score": 7.5,
            "mode": mode.title(),
        }

    async def cluster_signals(self, signals: list[Any]) -> dict[str, Any]:
        """
        Group signals into 3–5 thematic clusters using LLM analysis.

        Analyses signal titles and summaries to identify emerging themes
        across the dataset. Each theme includes a name, description, and
        list of associated signal IDs.

        Args:
            signals: List of SignalCard objects or dictionaries to cluster
                     (max 50 recommended for quality).

        Returns:
            Dictionary containing:
                - themes: List of theme dictionaries, each with:
                    - name: 2–4 word theme name
                    - description: One sentence explanation
                    - signal_ids: List of signal indices in this theme
                    - relevance_score: 0–10 strength indicator

        Raises:
            LLMServiceError: If the OpenAI API call fails.

        Example:
            >>> llm = LLMService(settings)
            >>> themes = await llm.cluster_signals(signal_list)
            >>> print(themes["themes"][0]["name"])
            "Bio-based Materials"
        """
        # Check if OpenAI client is available
        if not self.client:
            logger.warning("OpenAI client not initialized. Returning fallback response.")
            return {"themes": []}
        
        if not signals or len(signals) == 0:
            logger.info("No signals provided for clustering")
            return {"themes": []}
        
        # Convert SignalCard objects to simple dictionaries for the prompt
        signal_dicts = []
        for i, signal in enumerate(signals):
            # Handle both dict and object types
            if hasattr(signal, 'model_dump'):
                signal_data = signal.model_dump()
            elif isinstance(signal, dict):
                signal_data = signal
            else:
                signal_data = {
                    'title': getattr(signal, 'title', 'Unknown'),
                    'summary': getattr(signal, 'summary', '')
                }
            
            signal_dicts.append({
                'id': i,
                'title': signal_data.get('title', 'Unknown'),
                'summary': signal_data.get('summary', signal_data.get('abstract', ''))
            })
        
        # Build clustering prompt
        user_prompt = build_clustering_prompt(signal_dicts)
        
        messages = [
            {"role": "system", "content": CLUSTERING_INSTRUCTIONS},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # Call OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.4,  # Slightly higher for creative clustering
            )
            
            content = response.choices[0].message.content
            if content:
                result = json.loads(content)
                # Validate structure
                if 'themes' not in result:
                    logger.warning("LLM response missing 'themes' key")
                    return {"themes": []}
                return result
            else:
                return {"themes": []}
                
        except Exception as e:
            logger.error(f"LLM Clustering failed: {e}", exc_info=True)
            raise LLMServiceError(
                f"LLM clustering failed: {str(e)}",
                model=self.model,
            ) from e
