from __future__ import annotations

import httpx

from app.core.config import DEFAULT_SEARCH_RESULTS, SEARCH_TIMEOUT_SECONDS, Settings
from app.core.resilience import retry_with_backoff
from app.domain.taxonomy import TaxonomyService
from keywords import NICHE_DOMAINS, SIGNAL_KEYWORDS


class ServiceError(Exception):
    """Service error used for consistent API-level failure handling."""


class SearchService:
    """Google Search integration with taxonomy-aware query and friction logic."""

    FRICTION_TERMS: tuple[str, ...] = (
        '"unregulated"',
        '"black market"',
        '"hacky"',
        '"workaround"',
        '"grey market"',
        '"informal"',
    )

    def __init__(self, settings: Settings, taxonomy: TaxonomyService | None = None) -> None:
        self.settings = settings
        self.taxonomy = taxonomy or TaxonomyService()

    def calculate_trust(self, url: str) -> int:
        """Score URLs with a lightweight source trust heuristic."""
        score = 0
        if any(token in url for token in [".gov", ".edu", ".ac.uk", ".org"]):
            score += 20
        if url.endswith(".pdf"):
            score += 10
        return score

    def calculate_friction(self, query: str, friction_mode: bool) -> str:
        """Append entropy-style friction modifiers to widen search coverage."""
        if not friction_mode:
            return query
        return f"{query} ({' OR '.join(self.FRICTION_TERMS)})"

    def build_query(self, mission: str, topic: str, mode: str = "radar", *, friction_mode: bool = False) -> str:
        """Build taxonomy-driven search query with blacklist filtering."""
        mission_expansions = self.taxonomy.topic_expansions.get(mission, [])
        mode_terms = self.taxonomy.signal_types.get(mode, self.taxonomy.signal_types["radar"])
        blacklist_terms = " ".join([f"-{term}" for term in self.taxonomy.blacklist])

        expansion_terms = mission_expansions[:8]
        combined_expansions = " OR ".join([f'"{term}"' for term in expansion_terms])
        combined_modes = " OR ".join([f'"{term}"' for term in mode_terms[:6]])

        core_query = f'"{topic}"'
        if combined_expansions:
            core_query = f"{core_query} ({combined_expansions})"

        query = f"{mission} {core_query} ({combined_modes}) {blacklist_terms}".strip()
        return self.calculate_friction(query, friction_mode)

    @retry_with_backoff(retries=3, delay=1.0)
    async def search(
        self,
        query: str,
        num: int = DEFAULT_SEARCH_RESULTS,
        *,
        freshness: str | None = None,
        friction_mode: bool = False,
    ) -> list[dict]:
        """Execute Google custom search and return trust-sorted results."""
        if not self.settings.GOOGLE_SEARCH_API_KEY or not self.settings.GOOGLE_SEARCH_CX:
            raise ServiceError("Search API Key missing configuration.")

        effective_query = self.calculate_friction(query, friction_mode)
        params = {
            "key": self.settings.GOOGLE_SEARCH_API_KEY,
            "cx": self.settings.GOOGLE_SEARCH_CX,
            "q": effective_query,
            "num": num,
        }
        freshness_map = {"month": "qdr:m", "year": "qdr:y"}
        if freshness in freshness_map:
            params["tbs"] = freshness_map[freshness]

        try:
            async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT_SECONDS) as client:
                response = await client.get("https://www.googleapis.com/customsearch/v1", params=params)
                response.raise_for_status()
                items = response.json().get("items", [])
        except httpx.HTTPStatusError as exc:
            raise
        except httpx.HTTPError as exc:
            raise ServiceError(f"Search request failed: {exc}") from exc

        for item in items:
            item["trust"] = self.calculate_trust(item.get("link", ""))
        return sorted(items, key=lambda item: item.get("trust", 0), reverse=True)

    async def search_niche(self, query: str, *, friction_mode: bool = False) -> list[dict]:
        """Search for niche sources and boost niche domain trust."""
        novelty_query = f"{query} ({' OR '.join(SIGNAL_KEYWORDS[:3])})"
        results = await self.search(novelty_query, num=10, friction_mode=friction_mode)
        for item in results:
            item["is_niche"] = any(domain in item.get("link", "") for domain in NICHE_DOMAINS)
            if item["is_niche"]:
                item["trust"] = item.get("trust", 0) + 15
        return sorted(results, key=lambda item: item.get("trust", 0), reverse=True)
