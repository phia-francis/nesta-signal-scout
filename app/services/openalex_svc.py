from __future__ import annotations

import logging

import httpx

from app.core.config import SEARCH_TIMEOUT_SECONDS, Settings
from app.core.resilience import retry_with_backoff

logger = logging.getLogger(__name__)


class OpenAlexService:
    """OpenAlex client for research publication discovery."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @retry_with_backoff(retries=3, delay=1.0)
    async def search_works(self, topic: str, from_publication_date: str) -> list[dict]:
        """Search OpenAlex works and map to scan-friendly fields."""
        if not topic:
            return []

        headers: dict[str, str] = {
            "User-Agent": "Nesta Signal Scout (mailto:openalex@nesta.org.uk)",
        }
        if self.settings.OPENALEX_API_KEY:
            headers["api-key"] = self.settings.OPENALEX_API_KEY

        params = {
            "search": topic,
            "per_page": 10,
            "sort": "relevance_score:desc",
            "filter": f"from_publication_date:{from_publication_date}",
        }

        try:
            async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT_SECONDS) as client:
                response = await client.get(self.BASE_URL, params=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAlex API status for topic '%s': %s", topic, exc.response.status_code)
            raise
        except (httpx.HTTPError, ValueError) as exc:
            logger.error("OpenAlex request failed for topic '%s': %s", topic, exc)
            return []

        works = payload.get("results", [])
        mapped: list[dict] = []
        for work in works:
            cited_by_count = int(work.get("cited_by_count") or 0)
            mapped.append(
                {
                    "title": work.get("title") or "Untitled Work",
                    "url": work.get("doi") or work.get("id", ""),
                    "summary": work.get("display_name") or work.get("title") or "",
                    "activity": 0.0,
                    "attention": cited_by_count,
                    "cited_by_count": cited_by_count,
                    "publication_date": work.get("publication_date"),
                }
            )

        return mapped
