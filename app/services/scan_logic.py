from __future__ import annotations

from typing import Any

from app.core.config import SCAN_RESULT_LIMIT
from app.domain.models import RadarRequest
from app.domain.taxonomy import TaxonomyService


def _build_search_query(request: RadarRequest, taxonomy: TaxonomyService) -> tuple[str, str]:
    """Build a mode-aware external search query."""

    priorities = taxonomy.mission_priorities.get(request.mission, [])
    signal_terms = taxonomy.signal_types.get(request.mode, taxonomy.signal_types["radar"])
    joined_signals = " OR ".join([f'"{term}"' for term in signal_terms])

    if request.mode == "research":
        base_query = request.query if request.query else f"{request.mission} {request.topic or 'innovation'}"
        return "🔬 RESEARCH MODE: Global Academic Scan...", f"{base_query} ({joined_signals}) filetype:pdf -site:.com"

    if request.mode == "policy":
        return (
            "⚖️ POLICY MODE: International Policy & Strategy...",
            f"{request.mission} {request.topic or 'policy'} ({joined_signals}) (site:.gov OR site:.int OR site:.org)",
        )

    joined_blacklist = " ".join([f"-{word}" for word in taxonomy.blacklist])
    topic_value = (request.topic or "innovation").strip()
    if topic_value.lower() in taxonomy.generic_topics:
        pillars = " OR ".join([f'"{pillar}"' for pillar in priorities[:3]])
        return (
            "📡 RADAR MODE: Full Spectrum Scan (Industry + Policy + Academic)...",
            f"{request.mission} ({topic_value} AND ({pillars})) ({joined_signals}) {joined_blacklist}",
        )

    return (
        "📡 RADAR MODE: Full Spectrum Scan (Industry + Policy + Academic)...",
        f"{request.mission} {topic_value} ({joined_signals}) {joined_blacklist}",
    )


def _deduplicate_results(new_data: list[dict[str, Any]], existing_urls: set[str], url_key: str) -> list[dict[str, Any]]:
    """Filter result objects by URL membership in existing URLs."""

    return [item for item in new_data[:SCAN_RESULT_LIMIT] if item.get(url_key, "") not in existing_urls]
