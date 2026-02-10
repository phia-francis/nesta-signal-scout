from __future__ import annotations

from collections.abc import Mapping

import httpx

from app.core.config import SEARCH_TIMEOUT_SECONDS, Settings
from app.services.search_svc import ServiceError


class OpenAlexService:
    """OpenAlex client for research publication discovery."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def _reconstruct_abstract(abstract_index: Mapping[str, list[int]] | None) -> str:
        if not abstract_index:
            return ""

        positions_to_words: dict[int, str] = {}
        for word, positions in abstract_index.items():
            for position in positions:
                positions_to_words[position] = word

        return " ".join(word for _, word in sorted(positions_to_words.items()))

    async def search_works(self, query: str) -> list[dict]:
        """Search OpenAlex works and map to a simplified response model."""
        headers: dict[str, str] = {
            "User-Agent": "Nesta Signal Scout (mailto:openalex@nesta.org.uk)",
        }
        if self.settings.OPENALEX_API_KEY:
            headers["api-key"] = self.settings.OPENALEX_API_KEY

        params = {
            "search": query,
            "per_page": 10,
            "sort": "relevance_score:desc",
        }

        async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT_SECONDS) as client:
            response = await client.get(self.BASE_URL, params=params, headers=headers)
            if response.status_code != 200:
                raise ServiceError(f"OpenAlex API Error: {response.status_code}")

        works = response.json().get("results", [])
        if not works:
            raise ServiceError("OpenAlex returned no works for this topic.")

        simplified: list[dict] = []
        for work in works:
            title = work.get("title") or "Untitled Work"
            abstract = self._reconstruct_abstract(work.get("abstract_inverted_index"))
            publication_year = work.get("publication_year")
            if not abstract:
                abstract = (
                    f"{title} ({publication_year})"
                    if publication_year
                    else title
                )

            doi = work.get("doi")
            simplified.append(
                {
                    "title": title,
                    "url": doi or work.get("id", ""),
                    "summary": abstract,
                    "date": work.get("publication_date"),
                    "score": int(work.get("cited_by_count") or 0),
                }
            )

        return simplified
