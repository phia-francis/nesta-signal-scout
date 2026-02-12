"""
keywords.py
The Intelligence Core of Signal Scout.
"""

from openai import OpenAI

_client = None

# --- 1. NESTA MISSION PRIORITIES (Strategic Pillars) ---
MISSION_PRIORITIES = {
    "A Sustainable Future": ["Decarbonisation", "Retrofit Innovation", "Heat Pumps", "Green Skills", "Net Zero"],
    "A Healthy Life": ["Obesity Prevention", "Food Environments", "Nutritional Science", "Metabolic Health", "Health Equity"],
    "A Fairer Start": ["Early Childhood Development", "Childcare Innovation", "Parenting Tech", "Inequality in Education", "School Readiness"],
    "Cross-Cutting": ["Generative AI", "Digital Exclusion", "Systemic Change Levers", "Future of Work"],
}

# Backward-compatible aliases used elsewhere
MISSION_KEYWORDS = MISSION_PRIORITIES
CROSS_CUTTING_KEYWORDS = MISSION_PRIORITIES.get("Cross-Cutting", [])

# --- 2. TOPIC EXPANSIONS (The Granular Taxonomy) ---
TOPIC_EXPANSIONS = {
    "A Sustainable Future": [
        "bioenergy", "biomass heating", "geothermal energy", "solar power", "photovoltaic", "hydrogen energy",
        "micro chp", "renewable energy", "community energy", "district heating", "heat networks", "thermal storage",
        "retrofitting", "insulation", "smart grid", "energy storage", "battery storage", "flexibility markets",
        "low carbon home", "passivhaus", "EPC rating", "embodied carbon",
    ],
    "A Healthy Life": [
        "weight management", "GLP-1", "semaglutide", "ozempic", "wegovy", "mounjaro", "food swamp", "food desert",
        "HFSS", "sugar tax", "ultra-processed food", "UPF", "alternative protein", "cultivated meat",
        "precision fermentation", "vertical farming", "active travel", "micromobility", "e-scooter", "low traffic neighbourhood",
    ],
    "A Fairer Start": [
        "nursery", "preschool", "childminder", "early childhood education", "funded hours", "cognitive development",
        "socio-emotional skills", "language acquisition", "literacy", "numeracy", "executive function", "school readiness",
        "attainment gap", "free school meals", "neurodiversity", "autism", "ADHD", "parenting support", "edtech",
        "gamified learning", "adaptive learning", "baby tech",
    ],
}

# --- 3. SIGNAL MODES (The "How") ---
SIGNAL_TYPES = {
    "radar": ["startup", "innovation", "emerging trend", "venture capital", "seed round", "pilot project", "prototype", "breakthrough", "disruptive", "stealth mode"],
    "research": ["journal", "clinical trial", "randomised controlled trial", "RCT", "systematic review", "meta-analysis", "cohort study", "academic paper", "PhD thesis"],
    "policy": ["white paper", "green paper", "consultation", "legislation", "bill", "strategic framework", "policy briefing", "parliamentary report", "regulation"],
}

# Legacy export expected by services.py
SIGNAL_KEYWORDS = SIGNAL_TYPES["radar"]

# --- 4. NOISE FILTER ---
BLACKLIST = [
    "jobs", "hiring", "careers", "vacancy", "recruitment", "salary", "course", "webinar", "seminar", "masterclass",
    "training", "workshop", "coupon", "voucher", "discount", "promo code", "best of", "top 10", "linkedin.com",
    "facebook.com", "instagram.com", "pinterest.com",
]

# Legacy export expected by services.py
NICHE_DOMAINS = [
    "substack.com", "medium.com", "hackernoon.com", "arxiv.org", "biorxiv.org", "producthunt.com", "github.com",
    "wired.co.uk/topic/startups",
]

# --- 5. GENERIC TOPICS ---
GENERIC_TOPICS = ["obesity", "health", "energy", "education", "climate", "food"]


def generate_broad_scan_queries(seed_terms, num_signals=5):
    """Backward-compatible helper used by tests/agent logic."""
    global _client
    if _client is None:
        _client = OpenAI()

    prompt = (
        "Generate concise search queries for weak signal scanning. "
        f"Seed terms: {', '.join(seed_terms) if seed_terms else 'innovation'}. "
        f"Return exactly {num_signals} queries, one per line."
    )
    response = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You generate search queries for horizon scanning."},
            {"role": "user", "content": prompt},
        ],
    )
    content = response.choices[0].message.content or ""
    lines = [line.strip("•- ").strip() for line in content.splitlines() if line.strip()]
    if not lines:
        fallback = " ".join(seed_terms).strip() if seed_terms else "innovation trends"
        lines = [fallback]
    while len(lines) < num_signals:
        lines.append(lines[-1])
    return lines[:num_signals]
