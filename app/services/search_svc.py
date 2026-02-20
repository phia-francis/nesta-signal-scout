from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import SearchAPIError, RateLimitError

logger = logging.getLogger(__name__)

# Backward-compatible aliases so existing imports still work
ServiceError = SearchAPIError


class SearchService:
    """
    Google Custom Search API integration for web search.

    Handles search queries with exponential backoff for rate limits,
    structured error handling, and date-based filtering. Requires
    valid Google API key and Custom Search Engine ID.
    """

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, settings: Any = None) -> None:
        """
        Initialise the search service.

        Args:
            settings: Application settings containing API keys. Falls back
                      to global settings if not provided.
        """
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
        sort_by_date: bool = False,
        friction_mode: bool = False,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Execute a Google Custom Search query with retry logic.

        Performs a web search using Google's Custom Search API with optional
        date filtering and exponential backoff for rate limits. Results are
        returned as raw API response items.

        Args:
            query: Search query string.
            num: Number of results to return (max 10 per page).
            freshness: Date filter — 'day', 'week', 'month', or 'year'
                       (mapped to Google's dateRestrict parameter).
            sort_by_date: When ``True``, sort results by date (newest
                          first) using Google's ``sort=date`` parameter.
            friction_mode: Legacy parameter, ignored.
            max_retries: Maximum retry attempts for rate limits (default 3).

        Returns:
            List of search result dictionaries containing:
                - title: Result title
                - snippet: Result summary text
                - link: URL of the result
                - displayLink: Domain name

        Raises:
            SearchAPIError: If API keys are missing or the request fails.
            RateLimitError: If rate limit exceeded after all retries.

        Example:
            >>> service = SearchService(settings)
            >>> results = await service.search("climate tech", num=5)
            >>> print(results[0]["title"])
        """
        if not self.settings.GOOGLE_SEARCH_API_KEY or not self.settings.GOOGLE_SEARCH_CX:
            logger.error("Google Search API keys are missing. API_KEY present: %s, CX present: %s",
                        bool(self.settings.GOOGLE_SEARCH_API_KEY),
                        bool(self.settings.GOOGLE_SEARCH_CX))
            raise SearchAPIError("Google Search API keys are missing in configuration. Please check GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_CX environment variables.")

        # dateRestrict format: 'd[number]', 'w[number]', 'm[number]', 'y[number]'
        # We map simple strings to Google's format, or pass through validated raw values.
        _freshness_map = {"day": "d1", "week": "w1", "month": "m1", "year": "y1"}
        if freshness:
            date_restrict = _freshness_map.get(freshness)
            if date_restrict is None:
                if re.fullmatch(r"[dwmy]\d+", freshness):
                    date_restrict = freshness
                else:
                    raise SearchAPIError(
                        f"Invalid freshness value '{freshness}'. Must be 'day', 'week', 'month', 'year', or a raw dateRestrict like 'm3', 'y1'."
                    )
        else:
            date_restrict = None

        params = {
            "key": self.settings.GOOGLE_SEARCH_API_KEY,
            "cx": self.settings.GOOGLE_SEARCH_CX,
            "q": query,
            "num": min(10, num),  # Google API max per request
        }
        if date_restrict:
            params["dateRestrict"] = date_restrict
        if sort_by_date:
            params["sort"] = "date"

        logger.info(f"Google Search API call: query='{query}', num={num}, freshness={freshness}")

        # Exponential backoff for rate limits
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(self.BASE_URL, params=params)

                    # Handle specific error codes
                    if response.status_code == 403:
                        logger.error("Google API 403 Forbidden - likely invalid API key or quota exceeded")
                        raise SearchAPIError(
                            "Google API Error: 403 Forbidden. Please verify your API key is valid and you have remaining quota.",
                            status_code=403,
                        )
                    
                    if response.status_code == 429:
                        # Rate limit exceeded — parse Retry-After defensively
                        raw_retry = response.headers.get("Retry-After")
                        try:
                            retry_after = int(raw_retry) if raw_retry else 2 ** attempt
                        except (ValueError, TypeError):
                            retry_after = 2 ** attempt
                        logger.warning(f"Rate limit exceeded (429). Attempt {attempt + 1}/{max_retries}. Retrying after {retry_after}s...")
                        
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            logger.error("Rate limit exceeded after all retry attempts")
                            raise RateLimitError(
                                service="Google Search",
                                retry_after=retry_after,
                            )
                    
                    if response.status_code == 400:
                        logger.error(f"Bad request to Google API: {response.text}")
                        raise SearchAPIError(
                            "Google API Error: 400 Bad Request. Check your search query and parameters.",
                            status_code=400,
                        )
                    
                    if response.status_code >= 500:
                        logger.warning(
                            "Google API server error %d (attempt %d/%d): %s",
                            response.status_code, attempt + 1, max_retries, response.text,
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** (attempt + 1))
                            continue
                        else:
                            logger.error("Google API server error after all retries — returning empty results")
                            return []

                    if response.status_code != 200:
                        logger.error(f"Google API error {response.status_code}: {response.text}")
                        raise SearchAPIError(
                            f"Google Search API request failed with status {response.status_code}",
                            status_code=response.status_code,
                        )

                    data = response.json()
                    items = data.get("items", [])
                    logger.info(f"Google Search successful: query='{query}' returned {len(items)} results")
                    return items

            except httpx.TimeoutException as e:
                logger.error(f"Search timeout after 30s: {e}")
                raise SearchAPIError("Google Search API request timed out after 30 seconds. Please try again.") from e
            except httpx.RequestError as e:
                logger.error(f"Search Connection Error: {e}")
                raise SearchAPIError("Failed to connect to Google Search API. Please check your internet connection.") from e
            except (SearchAPIError, RateLimitError):
                # Re-raise our own exceptions without wrapping
                raise
            except Exception as e:
                logger.exception(f"Unexpected error during search: {e}")
                raise SearchAPIError(f"Search failed: {str(e)}") from e
        
        # Should not reach here, but just in case
        raise SearchAPIError("Search failed after all retries")
