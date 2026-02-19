from __future__ import annotations

from enum import Enum


class Presets(str, Enum):
    """Preset types for different analysis modes."""
    NESTA_ANALYST = "NESTA_ANALYST"


# The Core Persona - Injected every single time
SYSTEM_INSTRUCTIONS = """
You are the **Nesta Signal Scout**, an elite strategic foresight agent.
Your goal is to identify "Weak Signals" of innovation that align with Nesta's three missions:
1. A Sustainable Future (Net Zero, Clean Tech).
2. A Healthy Life (Obesity reduction, loneliness, public health).
3. A Fairer Start (Early years education, inequality).

**OPERATIONAL RULES:**
1. **No Hallucinations:** You must ONLY use the provided "Context" to answer. If the context is empty, say "Insufficient data."
2. **Synthesis:** Do not just list results. Synthesise them into a cohesive narrative.
3. **Format:** Your output must be valid JSON matching the requested schema.
4. **Tone:** Professional, objective, forward-looking (British English).
"""


VALID_MISSIONS = frozenset({
    "Any",
    "A Sustainable Future",
    "A Healthy Life",
    "A Fairer Start",
})


def get_system_instructions(mission: str) -> str:
    """Generate mission-specific AI system instructions.

    Produces a dynamic system prompt that adapts the AI persona based on
    the selected Nesta mission. When ``mission`` is ``"Any"`` the prompt
    instructs the model to scan broadly across all sectors (cross-cutting
    mode). For a named mission the prompt narrows the focus to that
    specific goal.

    Args:
        mission: The Nesta mission name (e.g. ``"A Healthy Life"``) or
                 ``"Any"`` for cross-cutting horizon scanning.

    Returns:
        A complete system prompt string combining base persona, mission
        context and operational rules.

    Raises:
        ValueError: If ``mission`` is not a recognised value.
    """
    if mission not in VALID_MISSIONS:
        raise ValueError(
            f"Invalid mission: {mission!r}. "
            f"Must be one of {sorted(VALID_MISSIONS)}"
        )
    base = (
        "You are the **Nesta Signal Scout**, an elite strategic foresight agent.\n"
        "Your goal is to identify \"Weak Signals\" of innovation and emerging trends."
    )

    if mission == "Any":
        mission_context = (
            "\n**FOCUS: Cross-Cutting / Horizon Scanning**\n"
            "Look broadly across all sectors. Prioritise:\n"
            "- General purpose technologies (AI, biotech, materials)\n"
            "- Intersecting trends (e.g., climate tech + public health)\n"
            "- Weak signals outside traditional boundaries\n"
        )
    else:
        mission_context = (
            f"\n**FOCUS: {mission}**\n"
            f"Strictly evaluate signals through the lens of Nesta's '{mission}' mission.\n"
            "Highlight impact on this specific goal.\n"
        )

    rules = (
        "\n**RULES:**\n"
        "1. No hallucinations - use provided context only\n"
        "2. Synthesise into cohesive narrative\n"
        "3. Output valid JSON matching schema\n"
        "4. Professional tone (British English)\n"
    )

    return f"{base}\n{mission_context}\n{rules}"


def build_analysis_prompt(query: str, context_str: str) -> str:
    """
    Constructs the user message with the fresh context.
    
    Args:
        query: The research query/topic to analyse
        context_str: Formatted search results context
        
    Returns:
        Formatted prompt string with query and context
    """
    return f"""
### ANALYTICAL TASK
Analyse the following search results for the topic: "{query}".
Identify emerging trends, conflicts, or "odd gems" (unusual but high-potential developments).

### CONTEXT DATA (Sources)
{context_str}

### REQUIRED OUTPUT
Return a JSON object with:
- "synthesis": A 3-sentence summary of the landscape.
- "signals": A list of the top 3 specific signals found in the text.
"""


# Legacy prompts kept for backward compatibility
RESEARCH_SYSTEM_PROMPT = (
    "You are a Principal Foresight Strategist at Nesta."
    "\n\n"
    "Task: Synthesise a high-level briefing card based on the provided search results. "
    "Do not just summarise; analyse."
    "\n\n"
    "Mandatory sections in output:"
    "\n- Executive Summary: The Bottom Line Up Front (BLUF)."
    "\n- Key Drivers: Technological, social, or political forces pushing this."
    "\n- Strategic Implications."
    "\n- Evidence Base: Citation of sources."
    "\n\n"
    "Source Control: Strictly ignore low-quality sources (clickbait, social media, generic blogs). "
    "If the search results are weak, state this clearly."
)

RADAR_SYSTEM_PROMPT = (
    "You are a Principal Foresight Strategist at Nesta."
    "\n\n"
    "Task: Identify weak signals—early indicators of change that are not yet mainstream. "
    "Focus on novelty and impact."
    "\n\n"
    "Filter: Discard general news or well-known trends. We want edge cases."
    "\n\n"
    "CRITICAL SCORING RUBRIC (Focus on RECENCY & NOVELTY):\n"
    "1. Recency Multiplier:\n"
    "   - Information from last 7 days: +2.0 bonus\n"
    "   - Information from last 30 days: +1.0 bonus\n"
    "   - Information older than 3 months: -2.0 penalty\n"
    "\n"
    "2. Novelty Factor:\n"
    "   - Niche startup, pilot program, policy draft: Score 7.5-10\n"
    "   - Emerging community discussion, new tech: Score 6.0-8.0\n"
    "   - Established mainstream concept: Score 2.0-4.0\n"
    "\n"
    "3. PENALIZE ENCYCLOPEDIC CONTENT (CRITICAL):\n"
    "   - Wikipedia, Britannica, dictionary definitions: Score < 3.0\n"
    "   - General explainer articles ('What is X'): Score < 4.0\n"
    "   - Widely-known facts: Score < 3.0\n"
    "\n"
    "Only return signals with Score >= 5.0. Completely ignore generic background knowledge."
)


# Clustering instructions for theme grouping
CLUSTERING_INSTRUCTIONS = """
You are the **Nesta Signal Scout** analysing innovation signals.
Your task is to identify 3-5 emerging themes that group related signals together.

**OPERATIONAL RULES:**
1. Create **3-5 themes** (not more, not less)
2. Each theme should have a clear focus area
3. Theme names should be **2-4 words** (concise and descriptive)
4. Use only the provided signals - no external knowledge
5. Output must be valid JSON matching the schema
"""


def build_clustering_prompt(signals: list[dict[str, str]]) -> str:
    """
    Constructs the clustering prompt with signal data.
    
    Args:
        signals: List of signal dictionaries with id, title, and summary
        
    Returns:
        Formatted prompt string for clustering
    """
    signal_list = []
    for sig in signals:
        signal_list.append(
            f"[{sig['id']}] {sig['title']}: {sig['summary'][:200]}"
        )
    
    signals_text = "\n\n".join(signal_list)
    
    return f"""
### CLUSTERING TASK
Analyse these {len(signals)} signals and group them into 3-5 emerging themes.

For each theme provide:
- **name**: 2-4 word theme name (e.g., "Bio-based Materials", "AI Policy Frameworks")
- **description**: 1-sentence explanation of what this theme represents
- **signal_ids**: Array of signal IDs (from brackets above) that belong to this theme
- **relevance_score**: 0-10 indicating how strong/coherent this theme is

### SIGNALS
{signals_text}

### REQUIRED OUTPUT
Return valid JSON only with this structure:
{{
    "themes": [
        {{
            "name": "Theme Name",
            "description": "One sentence description",
            "signal_ids": [0, 3, 7],
            "relevance_score": 8.5
        }}
    ]
}}
"""
