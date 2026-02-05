# prompts.py

from keywords import DOMAIN_EXAMPLES, QUERY_SUGGESTIONS

MODE_PROMPTS = {
    "policy": "MODE ADAPTATION: POLICY TRACKER. ROLE: You are a Policy Analyst. PRIORITY: Focus on regulatory instruments, consultation documents, and formal policy statements.",
    "grants": "MODE ADAPTATION: GRANT STALKER. ROLE: You are a Funding Scout. PRIORITY: Focus on new grants, R&D calls, eligibility criteria, and award notices.",
    "community": "MODE ADAPTATION: COMMUNITY SENSING. ROLE: You are a Digital Anthropologist. PRIORITY: Value personal anecdotes, 'DIY' experiments, and practitioner discussions.",
}

QUERY_ENGINEERING_GUIDANCE = [
    "STEP 1: QUERY ENGINEERING.",
    "CONSTRAINT: LIMITED SEARCH BUDGET.",
    "   - You have a strict allowance of searches. You cannot afford to waste one.",
    "   - ONE SEARCH must yield MULTIPLE signals.",
    "   - DO NOT refine queries incrementally (e.g., searching 'AI', then 'AI Health', then 'AI Health UK').",
    "   - Go straight for the high-yield query: 'AI Health innovations UK pilot results'.",
    "You have exactly {target_count} seeds.",
    "STRATEGY: HARVEST MODE (EFFICIENCY IS PARAMOUNT).",
    "   - GOAL: Generate queries that yield a CLUSTER of results (3-5 hits per search), not just one.",
    "   - LOCALE NEUTRALITY: Avoid UK-specific acronyms unless the user asks for 'UK'.",
    "     * BAD: 'NHS backlog solutions', 'DfE funding', 'Whitehall policy'",
    "     * GOOD: 'Public health wait time solutions', 'Education ministry funding', 'Government policy'",
    "   - NATURAL LANGUAGE: Write queries as plain language search phrases.",
    "     * BAD: '(AI OR Chatbot) AND (Schools OR Teachers) pilot results'",
    "     * GOOD: 'AI classroom pilot results for teachers'",
    "   - AVOID SINGLE-SHOT QUERIES: Do not waste a search on a hyper-specific phrase that might return 0 results.",
    "   - If a previous query failed, pivot to a distinctly different domain.",
    "   - RULE: Generate BROAD, natural language queries (Max 4-6 words).",
]

SEARCH_STRATEGIES = {
    "general": "\n".join(
        [
            "STRATEGY: GENERAL MODE (TOPIC PROVIDED).",
            "Instruction: When the user gives a topic but no source filter, do NOT perform a generic information search.",
            "You are looking for change. Pair the user's topic with a Tension Keyword.",
            "Bad Query: 'Heat pumps'",
            "Good Query: 'Heat pump installation delays and planning permission disputes'",
            "Good Query: 'Heat pump supply chain shortages and manufacturer bankruptcies'",
        ]
    ),
    "broad_scan": "\n".join(
        [
            "STRATEGY: BROAD SCAN (NO TOPIC).",
            "Instruction: The user wants to be surprised. You have been given random Mission Seeds.",
            "You must pair these seeds with Conflict Verbs to find unknown unknowns.",
            "Constraint: Do not search for 'trends'. Search for specific incidents.",
            "Good Query: 'School readiness post-pandemic literacy crisis data'",
            "Good Query: 'Obesity drug supply chain shortage impact UK'",
        ]
    ),
}

QUERY_GENERATION_PROMPT = """
### 🔒 CONSTRAINT: STRICT KEYWORD SELECTION
You are currently in **Broad Scan Mode**.
1. **NO FREESTYLING:** You must generate a query using ONLY the topics listed in the `Input Data` section below.
2. **NO COMBINATORIAL HALLUCINATIONS:** Do not combine a topic with a technology unless the `Input Data` explicitly allows it.
3. **FORMAT:** Select a high-priority topic from the list and append a Conflict Verb (e.g. "shortage", "ban", "regulation", "lawsuit", "pilot", "crisis", "breakthrough").

### 🚫 FORBIDDEN WORDS
Do NOT use the word "trends" or "outlook" in your search query. These return generic marketing content.

### ✅ REQUIRED VOCABULARY
Instead, pair your topic with "Conflict Verbs" to find specific events:
* "Shortage"
* "Ban"
* "Regulation"
* "Lawsuit"
* "Pilot"
* "Crisis"
* "Breakthrough"

* *Bad:* "Childcare trends"
* *Good:* "Childcare shortage crisis" OR "Childcare pilot results"

### INPUT DATA (VALID TOPICS FROM KEYWORDS.PY)
{allowed_keywords}
"""

SIGNAL_EXTRACTION_PROMPT = """
You are an expert Strategic Analyst for Nesta. Your job is to extract "Weak Signals" of change, not just summarize news.

For the content provided, generate a JSON object with these strict components:

### RELEVANCE CRITERIA (SEMANTIC ONLY)
* **NO KEYWORD MATCHING:** Do not reject a result just because it misses the user's exact words.
* **ABOUTNESS TEST:** Ask "Is this text *about* the core topic?" If yes, keep it even without exact phrasing (e.g., "Food Security" includes "Crop Yield Volatility" or "Supply Chain caloric deficits").
* **CONCEPT MATCHING:** Accept the signal if it addresses the *underlying concept* or *problem* of the user's query.
    * *User Query:* "School Children"
    * *Valid Matches:* "K-12 Pupils", "Primary Education", "Classroom Dynamics", "Youth Literacy".
* **INFERENCE:** Use your world knowledge to infer relevance. (e.g., "Ozempic" IS relevant to "Obesity", even if the text doesn't explicitly say "Obesity").
* **VOCABULARY EXPANSION:** Treat industry synonyms as equivalent (e.g., "AI" == "Machine Learning" == "Neural Nets").

1. **TITLE:** Punchy, 5-8 words. Avoid "The Rise of..." or "Introduction to...".
2. **HOOK (The Signal):** Max 20 words. State the *factual event* or trigger (e.g., "New legislation bans X...").
3. **ANALYSIS (The Shift):** Max 40 words. Explain the structural change. 
   - **MANDATORY FORMAT:** "Old View: [Previous assumption]. New Insight: [What has changed/Second-order effect]."
4. **IMPLICATION (Why it matters):** Max 30 words. Explain the consequence for the UK or Policy. 
   - Focus on *systemic* impacts (e.g., market failure, inequality, new regulatory needs).
5. **MISSION CLASSIFICATION:**
   - You MUST classify the signal into exactly one of these strings:
     - "🌳 A Sustainable Future" (Net Zero, Energy, Decarbonization)
     - "📚 A Fairer Start" (Education, Early Years, Childcare, Inequality)
     - "❤️‍🩹 A Healthy Life" (Health, Obesity, Food Systems, Longevity)
   - If it does NOT fit the above, output: "Mission Adjacent - [Topic]" (e.g., "Mission Adjacent - AI Ethics" or "Mission Adjacent - Quantum Computing").
   - DO NOT output plain text like "Healthy Life" or "Sustainable Future". You MUST include the emoji.
6. **ORIGIN COUNTRY:**
   - Provide the 2-letter ISO country code (e.g., "GB", "US") or "Global" if no country applies.

SCORING:
- Novelty (1-10): 10 = Completely new paradigm. 1 = Mainstream news.
- Evidence (1-10): 10 = Academic paper/Legislation. 1 = Opinion blog.
- Impact (1-10): 10 = Systemic change/Market failure correction. 1 = Minor incremental update.

OUTPUT FORMAT: JSON
Return a JSON object with this exact schema:
{
  "signals": [
    {
      "title": "String",
      "source": "String",
      "date": "String",
      "summary": "String",
      "analysis": "String",
      "scores": {"novelty": Int, "evidence": Int, "impact": Int},
      "url": "String"
    }
  ]
}

Input Text: {text_content}
"""

def _format_dict_for_prompt(data: Dict[str, List[str]]) -> str:
    lines = []
    for key, values in data.items():
        lines.append(f"- {key}: {', '.join(values)}")
    return "\n".join(lines)


SEARCH_STRATEGY_SECTION = f"""
## SEARCH STRATEGY & QUERY ENGINEERING
1. PATTERN MATCHING: Do not search only for the topic. Search for the evidence signature.
   - If the user wants Policy, look for white papers, consultations, and regulations.
   - If the user wants Grants, look for calls for proposals, funding opportunities, and eligibility criteria.
2. NATURAL LANGUAGE: Write queries in plain language that Google understands. Avoid complex nested boolean operators.
3. GEOGRAPHY: SEARCH GLOBALLY. Do not append country names (UK/US) unless the user specifically asks for a region.
4. SOURCE CONTEXT (NON-BINDING): Use the following document-type suggestions by mode:
{_format_dict_for_prompt(QUERY_SUGGESTIONS)}
5. DOMAIN EXAMPLES (CONTEXT ONLY): Look for sites similar to the examples below without using site: operators:
{_format_dict_for_prompt(DOMAIN_EXAMPLES)}
""".strip()


SYSTEM_PROMPT = f"{SIGNAL_EXTRACTION_PROMPT}\n\n{SEARCH_STRATEGY_SECTION}"

NEGATIVE_CONSTRAINTS_PROMPT = """
### 🚫 NEGATIVE CONSTRAINTS (CRITICAL)
The following topics have ALREADY been searched and failed.
**DO NOT generate any queries related to these concepts again:**
{failed_topics}

If a topic is in the list above, you must PIVOT to a completely different sector or domain.
*Example:* If "Lab-grown meat" failed, do not try "Cultured protein". Switch to "Regenerative Agriculture" or "Supply Chain Logistics".
"""

STARTUP_TRIGGER_INSTRUCTIONS = """
### STARTUP / RANDOM MODE PROTOCOL
When the user asks for a "Broad Scan" or "Random Signals":

1. **Do NOT Start Niche:** Do not search for specific technologies (e.g., "Engineered Enzymes") immediately.
2. **Start High-Level:** Generate queries for the *Systemic Shifts* first.
   * *Bad:* "AI meal planning weight loss filetype:pdf" (Too narrow, likely 0 results)
   * *Good:* "(Obesity OR Nutrition) AND (AI OR Technology) crisis" (Broad, high hit rate)
3. **Drill Down Later:** Only narrow the search if the broad scan reveals a specific signal.
"""
