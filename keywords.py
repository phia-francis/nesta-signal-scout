"""
keywords.py
The Intelligence Core of Signal Scout.
"""

# --- 1. NESTA MISSION PRIORITIES (Strategic Pillars) ---
# These are the high-level themes that define the mission scope.
MISSION_PRIORITIES = {
    "A Sustainable Future": [
        "Decarbonisation",
        "Retrofit Innovation",
        "Heat Pumps",
        "Green Skills",
        "Net Zero",
    ],
    "A Healthy Life": [
        "Obesity Prevention",
        "Food Environments",
        "Nutritional Science",
        "Metabolic Health",
        "Health Equity",
    ],
    "A Fairer Start": [
        "Early Childhood Development",
        "Childcare Innovation",
        "Parenting Tech",
        "Inequality in Education",
        "School Readiness",
    ],
    "Cross-Cutting": [
        "Generative AI",
        "Digital Exclusion",
        "Systemic Change Levers",
        "Future of Work",
    ],
}

# --- 2. TOPIC EXPANSIONS (The Granular Taxonomy) ---
# Specific terms used to broaden the search net.
# Derived from 'Auto horizon scanning' datasets.
TOPIC_EXPANSIONS = {
    "A Sustainable Future": [
        "bioenergy",
        "biomass heating",
        "geothermal energy",
        "solar power",
        "photovoltaic",
        "hydrogen energy",
        "micro chp",
        "renewable energy",
        "community energy",
        "district heating",
        "heat networks",
        "thermal storage",
        "retrofitting",
        "insulation",
        "smart grid",
        "energy storage",
        "battery storage",
        "flexibility markets",
        "low carbon home",
        "passivhaus",
        "EPC rating",
        "embodied carbon",
    ],
    "A Healthy Life": [
        "weight management",
        "GLP-1",
        "semaglutide",
        "ozempic",
        "wegovy",
        "mounjaro",
        "food swamp",
        "food desert",
        "HFSS",
        "sugar tax",
        "ultra-processed food",
        "UPF",
        "alternative protein",
        "cultivated meat",
        "precision fermentation",
        "vertical farming",
        "active travel",
        "micromobility",
        "e-scooter",
        "low traffic neighbourhood",
    ],
    "A Fairer Start": [
        "nursery",
        "preschool",
        "childminder",
        "early childhood education",
        "funded hours",
        "cognitive development",
        "socio-emotional skills",
        "language acquisition",
        "literacy",
        "numeracy",
        "executive function",
        "school readiness",
        "attainment gap",
        "free school meals",
        "neurodiversity",
        "autism",
        "ADHD",
        "parenting support",
        "edtech",
        "gamified learning",
        "adaptive learning",
        "baby tech",
    ],
}

# --- 3. SIGNAL MODES (The "How") ---
SIGNAL_TYPES = {
    "radar": [
        "startup",
        "innovation",
        "emerging trend",
        "venture capital",
        "seed round",
        "pilot project",
        "prototype",
        "breakthrough",
        "disruptive",
        "stealth mode",
    ],
    "research": [
        "journal",
        "clinical trial",
        "randomised controlled trial",
        "RCT",
        "systematic review",
        "meta-analysis",
        "cohort study",
        "academic paper",
        "PhD thesis",
    ],
    "policy": [
        "white paper",
        "green paper",
        "consultation",
        "legislation",
        "bill",
        "strategic framework",
        "policy briefing",
        "parliamentary report",
        "regulation",
    ],
}

# --- 4. NOISE FILTER ---
BLACKLIST = [
    "jobs",
    "hiring",
    "careers",
    "vacancy",
    "recruitment",
    "salary",
    "course",
    "webinar",
    "seminar",
    "masterclass",
    "training",
    "workshop",
    "coupon",
    "voucher",
    "discount",
    "promo code",
    "best of",
    "top 10",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "pinterest.com",
]

# --- 5. GENERIC TOPICS ---
GENERIC_TOPICS = [
    "obesity",
    "health",
    "energy",
    "education",
    "climate",
    "food",
]
