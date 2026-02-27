from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, cast

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
        self.client: AsyncOpenAI | None
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
                messages=cast(Any, messages),
                response_format=cast(Any, {"type": "json_object"}),
                temperature=0.3,  # Low temperature for factual grounding
            )
            
            content = response.choices[0].message.content
            if content:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return cast(dict[str, Any], parsed)
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
                messages=cast(Any, [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context},
                ]),
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

    async def evaluate_radar_signals(self, query: str, search_results: list[dict[str, Any]], mission: str) -> list[dict[str, Any]]:
        """Evaluate and rewrite raw search results for radar mode to prevent copy-pasting."""
        if not self.client:
            return []

        buffer = []
        for item in search_results:
            # Inject numerical ID so the LLM can precisely map summaries back to the original URLs
            buffer.append(f"[{item.get('id')}] {item.get('title')} ({item.get('displayLink')}): {item.get('snippet')}")
        context_str = "\n\n".join(buffer)

        if not context_str.strip():
            return []

        try:
            system_prompt = get_system_instructions(mission)
        except ValueError:
            # Fall back gracefully for unknown missions (e.g. API default "General")
            try:
                system_prompt = get_system_instructions("Any")
            except ValueError:
                system_prompt = SYSTEM_INSTRUCTIONS
        user_prompt = f"""
### RADAR EVALUATION TASK
Review the following search results for the topic: "{query}".
Identify and rewrite up to 10 of the most relevant, novel signals from the context.

### CONTEXT DATA
{context_str}

### REQUIRED OUTPUT
Return valid JSON with a "signals" array. Each object MUST contain:
- "id": The exact numerical ID from the brackets in the context data (critical for matching).
- "title": A descriptive, engaging title.
- "summary": A 2-3 sentence critical analysis. DO NOT copy-paste the snippet. Explain the core innovation, drivers, and strategic implications.
- "score": A relevance score (1.0-10.0).
- "confidence": AI confidence score (1-100).
- "origin_country": Intelligently deduce the geographical origin (e.g., "UK", "USA", "Global") based on the publisher, URL, or content.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=cast(Any, messages),
                response_format=cast(Any, {"type": "json_object"}),
                temperature=0.3,
            )
            content = response.choices[0].message.content
            if content:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    signals = parsed.get("signals", [])
                    if isinstance(signals, list):
                        return [cast(dict[str, Any], signal) for signal in signals if isinstance(signal, dict)]
            return []
        except Exception as e:
            logger.error("Radar evaluation failed: %s", e)
            return []

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
                messages=cast(Any, messages),
                response_format=cast(Any, {"type": "json_object"}),
                temperature=0.4,  # Slightly higher for creative clustering
            )
            
            content = response.choices[0].message.content
            if content:
                result = json.loads(content)
                # Validate structure
                if isinstance(result, dict):
                    if 'themes' not in result:
                        logger.warning("LLM response missing 'themes' key")
                        return {"themes": []}
                    return cast(dict[str, Any], result)
                return {"themes": []}
            else:
                return {"themes": []}
                
        except Exception as e:
            logger.error(f"LLM Clustering failed: {e}", exc_info=True)
            raise LLMServiceError(
                f"LLM clustering failed: {str(e)}",
                model=self.model,
            ) from e

    async def analyze_trend_clusters(self, clusters_data: list[dict[str, Any]], mission: str) -> list[dict[str, Any]]:
        """Analyses ML-generated clusters and returns a macro-trend summary and strength rating for each."""
        if not self.client:
            logger.warning("OpenAI client not initialized. Skipping cluster analysis.")
            return []

        prompt = f"""
    You are a Lead Horizon Scanning Analyst for the '{mission}' mission.
    I am providing you with clusters of signals grouped by an ML algorithm.

    For EACH cluster, analyse the signal summaries collectively and articulate the macro-trend.

    Determine 'Emerging Strength' using this criteria:
    - Strong: Multiple highly coherent signals from diverse or authoritative sources.
    - Moderate: A few signals pointing the same direction, lacking widespread momentum.
    - Weak: Vague, disparate, or speculative signals with weak consensus.

    Return a JSON object with key "trend_analyses" containing an array of objects with:
    - cluster_name: Keep the original name provided.
    - trend_summary: 2-3 sentence analytical summary of the macro-trend.
    - strength: Exactly one of ["Strong", "Moderate", "Weak"].
    - reasoning: 1 sentence explaining the strength rating based on evidence.

    CLUSTERS TO ANALYSE:
    {json.dumps(clusters_data, indent=2)}
    """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=cast(Any, [{"role": "system", "content": prompt}]),
                temperature=0.3,
                response_format=cast(Any, {"type": "json_object"})
            )
            raw_content = response.choices[0].message.content
            if not raw_content:
                return []
            content = json.loads(raw_content)
            if isinstance(content, dict):
                trend_analyses = content.get("trend_analyses", [])
                if isinstance(trend_analyses, list):
                    return [cast(dict[str, Any], analysis) for analysis in trend_analyses if isinstance(analysis, dict)]
            return []
        except Exception as e:
            logging.error(f"Cluster LLM analysis failed: {e}")
            return []

    async def generate_agentic_queries(
        self, topic: str, mode: str, mission: str, num_queries: int
    ) -> list[str]:
        """Generate unbiased, mode-aware search queries via the LLM."""

        mode_instructions = {
            "radar": "Focus on broad, emerging trends, weak signals, and early-stage innovations across different sectors.",
            "research": "Focus on deep analysis, academic breakthroughs, technological deep-dives, and whitepapers.",
            "governance": (
                "Focus on global policy updates, parliament debates, regulatory shifts, and international "
                "think-tank publications. Do NOT bias any specific country (e.g. do not just look at UK/US)."
            ),
        }

        prompt = f"""
You are an expert Horizon Scanner and OSINT analyst working for Nesta's '{mission}' mission.
Your task is to generate {num_queries} distinct, highly effective Google Search queries to investigate: "{topic}".

MODE CONTEXT: {mode_instructions.get(mode, mode_instructions['radar'])}

RULES:
1. Queries must capture different angles of the topic.
2. Do NOT use hardcoded site operators (e.g. site:.gov.uk). Keep it global.
3. Use advanced operators (AND, OR, "") naturally to surface high-quality reports and trends.
4. Return a JSON object with a single key "queries" containing an array of strings. Example: {{"queries": ["query 1", "query 2", "query 3"]}}
"""

        if not self.client:
            return [f"{topic} emerging trends", f"{topic} global policy", f"{topic} breakthrough"]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=cast(Any, [{"role": "system", "content": prompt}]),
                temperature=0.4,
                max_tokens=300,
                response_format=(cast(Any, {"type": "json_object"}) if "gpt" in self.model else cast(Any, None)),
            )
            content = response.choices[0].message.content
            if content:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    queries = parsed.get("queries", next(iter(parsed.values())))
                    if isinstance(queries, list):
                        return [str(query) for query in queries]
                    return [str(queries)]
                if isinstance(parsed, list):
                    return [str(query) for query in parsed]
                return [str(parsed)]
            return [f"{topic} emerging trends", f"{topic} global policy", f"{topic} breakthrough"]
        except Exception as e:
            logging.error("Failed to generate queries: %s", e)
            return [f"{topic} emerging trends", f"{topic} global policy", f"{topic} breakthrough"]

    async def verify_and_synthesize(
        self, raw_results: list[dict[str, Any]], topic: str, mission: str, mode: str
    ) -> list[dict[str, Any]]:
        """Strictly evaluate search results, discard hallucinations, and format verified signals."""

        if not self.client:
            return []

        now = datetime.now(timezone.utc)
        current_date_str = now.strftime("%B %d, %Y")
        one_year_ago_str = (now - timedelta(days=365)).strftime("%B %d, %Y")

        results_json = json.dumps(raw_results, indent=2)
        prompt = f"""
    You are a rigorous Horizon Scanning Fact-Checker for the '{mission}' mission.
    You are reviewing raw search API results for the topic: "{topic}" (Mode: {mode}).

    CURRENT DATE: {current_date_str}
    ABSOLUTE CUTOFF DATE: {one_year_ago_str}

    RULES FOR DISCARDING:
    1. DISCARD if the source is explicitly dated before {one_year_ago_str}. Prioritise recency (past 1–3 months).
    2. DISCARD if the snippet does not describe an emerging trend, innovation, or policy shift.
    3. DISCARD if the URL is a generic homepage, broken link, or irrelevant directory.
    4. DISCARD if the snippet is too vague to support the title's claim.

    For sources that pass verification, return a JSON object with a single key "signals"
    containing an array of objects with these exact keys:
    - title: A concise, accurate title.
    - summary: A 2-sentence analytical summary of the trend.
    - url: The EXACT URL from the raw results input. DO NOT alter, truncate, or hallucinate this URL. Copy it character for character.
    - date: Publication date in YYYY-MM-DD format, if available. If the publication date is unknown, use null or omit this field.
    - score: Novelty/impact score from 1.0 to 10.0. Score higher for more recent signals.
    - origin_country: Intelligently deduce the geographical origin of this signal (e.g., "UK", "USA", "Germany"). Use the source URL, publisher, or content context. If it represents an international effort or is ambiguous, output "Global".

    RAW RESULTS TO EVALUATE:
    {results_json}
    """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=cast(Any, [{"role": "system", "content": prompt}]),
                temperature=0.2,
                max_tokens=2000,
                response_format=cast(Any, {"type": "json_object"})
            )
            raw = response.choices[0].message.content
            if not raw:
                return []
            content = json.loads(raw)
            if isinstance(content, dict):
                signals = content.get("signals", [])
                if isinstance(signals, list):
                    return [cast(dict[str, Any], signal) for signal in signals if isinstance(signal, dict)]
            return []
        except Exception as e:
            logging.error("Verification failed", exc_info=True)
            return []
