from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.prompts import (
    SYSTEM_INSTRUCTIONS, 
    build_analysis_prompt,
    CLUSTERING_INSTRUCTIONS,
    build_clustering_prompt
)

logger = logging.getLogger(__name__)


class LLMService:
    """
    Stateless Service for AI Synthesis.
    Each call is a fresh 'Zero-Shot' interaction with full context injection.
    """

    def __init__(self, settings: Any = None) -> None:
        self.settings = settings or get_settings()
        # Only initialize OpenAI client if API key is available
        if self.settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
        else:
            self.client = None
            logger.warning("LLMService initialized without OPENAI_API_KEY. Synthesis will not be available.")
        self.model = self.settings.CHAT_MODEL

    async def synthesize_research(self, query: str, search_results: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Takes raw search results -> Formats into Context -> Calls LLM -> Returns JSON.
        
        Args:
            query: The research query/topic
            search_results: List of search result dictionaries
            
        Returns:
            Dictionary with 'synthesis' and 'signals' keys
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
        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
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
            return {"synthesis": "Error generating insight.", "signals": []}

    def _format_results_for_llm(self, results: list[dict[str, Any]]) -> str:
        """
        Converts complex JSON search results into a dense text block for the AI.
        
        Args:
            results: List of search result dictionaries
            
        Returns:
            Formatted string with numbered results
        """
        buffer = []
        for i, item in enumerate(results[:15], 1):  # Limit to top 15 to save tokens
            title = item.get("title", "Unknown")
            snippet = item.get("snippet", item.get("abstract", "No summary"))
            source = item.get("displayLink", item.get("source", "Unknown Source"))
            buffer.append(f"[{i}] {title} ({source}): {snippet}")
        return "\n\n".join(buffer)

    async def cluster_signals(self, signals: list[Any]) -> dict[str, Any]:
        """
        Groups signals into 3-5 emerging themes using LLM analysis.
        
        Args:
            signals: List of SignalCard objects to cluster
            
        Returns:
            Dictionary with 'themes' key containing list of theme objects:
            {
                "themes": [
                    {
                        "name": "Bio-based Materials",
                        "description": "Emerging sustainable construction...",
                        "signal_ids": [0, 3, 7],
                        "relevance_score": 8.5
                    }
                ]
            }
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
            return {"themes": []}
