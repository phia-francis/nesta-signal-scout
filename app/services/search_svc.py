from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Raised when an external service fails."""
    pass


class SearchService:
    """
    Client for Google Custom Search JSON API.
    STRICT MODE: No mock data. Fails if API key is missing or request fails.
    """

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        if not self.settings.GOOGLE_SEARCH_API_KEY or not self.settings.GOOGLE_SEARCH_CX:
            # We log a warning but don't crash init, in case only other modes are used.
            # However, calling search() will fail.
            logger.warning("SearchService initialized without API keys. Search will fail.")

    async def search(
        self,
        query: str,
        num: int = 10,
        freshness: str | None = None,
        friction_mode: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Execute a real Google Search.

        Args:
            query: The search term.
            num: Number of results (max 10 per page, logic handles paging if needed).
            freshness: 'day', 'week', 'month', 'year' (maps to dateRestrict).
            friction_mode: If True, ignored (legacy param).

        Returns:
            List of result dicts from Google.

        Raises:
            ServiceError: If the API call fails or keys are missing.
        """
        if not self.settings.GOOGLE_SEARCH_API_KEY or not self.settings.GOOGLE_SEARCH_CX:
            raise ServiceError("Google Search API keys are missing in configuration.")

        # dateRestrict format: 'd[number]', 'w[number]', 'm[number]', 'y[number]'
        # We map simple strings to Google's format.
        date_restrict = None
        if freshness == "day": date_restrict = "d1"
        elif freshness == "week": date_restrict = "w1"
        elif freshness == "month": date_restrict = "m1"
        elif freshness == "year": date_restrict = "y1"

        params = {
            "key": self.settings.GOOGLE_SEARCH_API_KEY,
            "cx": self.settings.GOOGLE_SEARCH_CX,
            "q": query,
            "num": min(10, num),  # Google API max per request
        }
        if date_restrict:
            params["dateRestrict"] = date_restrict

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, params=params)

                if response.status_code == 403:
                    raise ServiceError("Google API Error: 403 Forbidden (Check Quota or Keys).")
                if response.status_code != 200:
                    response.raise_for_status()

                data = response.json()
                items = data.get("items", [])
                logger.info(f"Google Search query='{query}' returned {len(items)} results.")
                return items

        except httpx.HTTPStatusError as e:
            logger.error(f"Search HTTP Error: {e.response.text}")
            raise ServiceError(f"Upstream Search API Failed: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Search Connection Error: {e}")
            raise ServiceError("Failed to connect to Search API.")
        except Exception as e:
            logger.exception("Unexpected error during search.")
            raise ServiceError(f"Search failed: {str(e)}")
