from openai import OpenAI


_client = None


def _k(s):
    return [l.strip() for l in s.strip().splitlines() if l.strip()]


MISSION_KEYWORDS = {
    "A Fairer Start": _k(
        """
        Early Childhood Development
        Childcare Innovation
        Parenting Tech
        Inequality in Education
        """
    ),
    "A Healthy Life": _k(
        """
        Obesity Prevention
        Food Environments
        Nutritional Science
        Metabolic Health
        """
    ),
    "A Sustainable Future": _k(
        """
        Decarbonisation
        Retrofit Innovation
        Heat Pumps
        Green Skills
        """
    ),
    "Cross-Cutting": _k(
        """
        Generative AI
        Digital Exclusion
        Systemic Change Levers
        Future of Work
        """
    ),
}

CROSS_CUTTING_KEYWORDS = MISSION_KEYWORDS.get("Cross-Cutting", [])

TRUST_BOOST_TLDS = [".gov", ".edu", ".ac.uk", ".int", ".mil", ".org"]
BLOCKLIST_DOMAINS = ["facebook.com", "instagram.com", "twitter.com", "pinterest.com"]

# Terms that indicate early-stage novelty
SIGNAL_KEYWORDS = [
    "experimental",
    "prototype",
    "proof of concept",
    "unconventional",
    "novel approach",
    "emerging paradigm",
    "stealth mode",
    "pre-seed",
    "grassroots",
]

# Niche/Novelty Sources (Allow-list for Discovery Mode)
NICHE_DOMAINS = [
    "substack.com",
    "medium.com",
    "hackernoon.com",
    "arxiv.org",
    "biorxiv.org",
    "producthunt.com",
    "github.com",
    "wired.co.uk/topic/startups",
]


def generate_broad_scan_queries(seed_terms, num_signals=5):
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
