from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Raised when an external service fails."""
    pass


class RateLimitError(ServiceError):
    """Raised when API rate limit is exceeded."""
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
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Execute a real Google Search with exponential backoff for rate limits.

        Args:
            query: The search term.
            num: Number of results (max 10 per page, logic handles paging if needed).
            freshness: 'day', 'week', 'month', 'year' (maps to dateRestrict).
            friction_mode: If True, ignored (legacy param).
            max_retries: Maximum number of retry attempts for rate limits (default: 3).

        Returns:
            List of result dicts from Google.

        Raises:
            ServiceError: If the API call fails or keys are missing.
            RateLimitError: If rate limit exceeded after all retries.
        """
        if not self.settings.GOOGLE_SEARCH_API_KEY or not self.settings.GOOGLE_SEARCH_CX:
            logger.error("Google Search API keys are missing. API_KEY present: %s, CX present: %s",
                        bool(self.settings.GOOGLE_SEARCH_API_KEY),
                        bool(self.settings.GOOGLE_SEARCH_CX))
            raise ServiceError("Google Search API keys are missing in configuration. Please check GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_CX environment variables.")

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

        logger.info(f"Google Search API call: query='{query}', num={num}, freshness={freshness}")

        # Exponential backoff for rate limits
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(self.BASE_URL, params=params)

                    # Handle specific error codes
                    if response.status_code == 403:
                        logger.error("Google API 403 Forbidden - likely invalid API key or quota exceeded")
                        raise ServiceError("Google API Error: 403 Forbidden. Please verify your API key is valid and you have remaining quota.")
                    
                    if response.status_code == 429:
                        # Rate limit exceeded
                        retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                        logger.warning(f"Rate limit exceeded (429). Attempt {attempt + 1}/{max_retries}. Retrying after {retry_after}s...")
                        
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            logger.error("Rate limit exceeded after all retry attempts")
                            raise RateLimitError(f"Google Search API rate limit exceeded after {max_retries} attempts. Please try again later.")
                    
                    if response.status_code == 400:
                        logger.error(f"Bad request to Google API: {response.text}")
                        raise ServiceError("Google API Error: 400 Bad Request. Check your search query and parameters.")
                    
                    if response.status_code != 200:
                        logger.error(f"Google API error {response.status_code}: {response.text}")
                        response.raise_for_status()

                    data = response.json()
                    items = data.get("items", [])
                    logger.info(f"Google Search successful: query='{query}' returned {len(items)} results")
                    return items

            except httpx.TimeoutException as e:
                logger.error(f"Search timeout after 30s: {e}")
                raise ServiceError("Google Search API request timed out after 30 seconds. Please try again.")
            except httpx.HTTPStatusError as e:
                logger.error(f"Search HTTP Error {e.response.status_code}: {e.response.text}")
                raise ServiceError(f"Google Search API request failed with status {e.response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"Search Connection Error: {e}")
                raise ServiceError("Failed to connect to Google Search API. Please check your internet connection.")
            except Exception as e:
                logger.exception(f"Unexpected error during search: {e}")
                raise ServiceError(f"Search failed: {str(e)}")
        
        # Should not reach here, but just in case
        raise ServiceError("Search failed after all retries")
