from __future__ import annotations

import logging
from typing import Any, cast

import httpx

from app.core.config import SEARCH_TIMEOUT_SECONDS, Settings
from app.core.exceptions import OpenAlexAPIError
from app.core.resilience import retry_with_backoff

logger = logging.getLogger(__name__)


class OpenAlexService:
    """
    OpenAlex client for research publication discovery.

    Queries the OpenAlex API to find academic works by topic, returning
    results sorted by relevance. Supports optional date filtering and
    automatic retry with backoff.
    """

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, settings: Settings) -> None:
        """
        Initialise the OpenAlex service.

        Args:
            settings: Application settings containing optional OpenAlex API key.
        """
        self.settings = settings

    @retry_with_backoff(retries=3, delay=1.0)
    async def search_works(self, topic: str, from_publication_date: str = "") -> list[dict[str, Any]]:
        """
        Search OpenAlex works and map results to scan-friendly fields.

        Queries the OpenAlex API for academic works matching the given topic,
        filtered by publication date, and returns a simplified dictionary
        format compatible with the scan pipeline.

        Args:
            topic: Search topic string.
            from_publication_date: ISO-format date string (e.g. '2024-01-01')
                                   to filter works published on or after.

        Returns:
            List of dictionaries, each containing:
                - title: Work title
                - url: DOI or OpenAlex ID
                - summary: Display name or title
                - activity: Always 0.0 (not applicable)
                - attention: Citation count
                - cited_by_count: Number of citations
                - publication_date: ISO date string or None

        Raises:
            OpenAlexAPIError: If the API returns an HTTP error status.
        """
        if not topic:
            return []

        headers: dict[str, str] = {
            "User-Agent": "Nesta Signal Scout (mailto:openalex@nesta.org.uk)",
        }
        if self.settings.OPENALEX_API_KEY:
            headers["api-key"] = self.settings.OPENALEX_API_KEY

        params: dict[str, str | int] = {
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
            raise OpenAlexAPIError(
                f"OpenAlex API request failed with status {exc.response.status_code}"
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            logger.error("OpenAlex request failed for topic '%s': %s", topic, exc)
            return []

        works = payload.get("results", []) if isinstance(payload, dict) else []
        mapped: list[dict[str, Any]] = []
        for work in works:
            if not isinstance(work, dict):
                continue
            work = cast(dict[str, Any], work)
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
