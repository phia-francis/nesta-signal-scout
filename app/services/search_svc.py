from __future__ import annotations

import httpx

from app.core.config import DEFAULT_SEARCH_RESULTS, SEARCH_TIMEOUT_SECONDS, Settings
from keywords import NICHE_DOMAINS, SIGNAL_KEYWORDS


class ServiceError(Exception):
    """Service error used for consistent API-level failure handling."""


class SearchService:
    """Google Search integration with trust scoring and friction modifiers."""

    FRICTION_TERMS: tuple[str, ...] = (
        '"unregulated"',
        '"black market"',
        '"workaround"',
        '"grey market"',
        '"informal"',
    )

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def calculate_trust(self, url: str) -> int:
        """Score URLs with a lightweight source trust heuristic."""
        score = 0
        if any(token in url for token in [".gov", ".edu", ".ac.uk", ".org"]):
            score += 20
        if url.endswith(".pdf"):
            score += 10
        return score

    def apply_friction_modifiers(self, query: str, friction_mode: bool) -> str:
        """Append friction modifiers when friction mode is enabled."""
        if not friction_mode:
            return query
        return f"{query} ({' OR '.join(self.FRICTION_TERMS)})"

    async def search(
        self,
        query: str,
        num: int = DEFAULT_SEARCH_RESULTS,
        *,
        friction_mode: bool = False,
    ) -> list[dict]:
        """Execute Google custom search and return trust-sorted results."""
        if not self.settings.GOOGLE_SEARCH_API_KEY or not self.settings.GOOGLE_SEARCH_CX:
            raise ServiceError("Search API Key missing configuration.")

        effective_query = self.apply_friction_modifiers(query, friction_mode)
        params = {
            "key": self.settings.GOOGLE_SEARCH_API_KEY,
            "cx": self.settings.GOOGLE_SEARCH_CX,
            "q": effective_query,
            "num": num,
        }
        async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT_SECONDS) as client:
            response = await client.get("https://www.googleapis.com/customsearch/v1", params=params)
            if response.status_code != 200:
                raise ServiceError(f"Search API Error: {response.status_code}")
            items = response.json().get("items", [])

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
