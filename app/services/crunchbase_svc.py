from __future__ import annotations

import httpx

from app.core.config import SEARCH_TIMEOUT_SECONDS, Settings
from app.services.search_svc import ServiceError


class CrunchbaseService:
    """Crunchbase client for funding and company deal activity."""

    BASE_URL = "https://api.crunchbase.com/api/v4"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def fetch_deals(self, query: str) -> list[dict]:
        """Fetch organisation funding data for a given topic query."""
        if not self.settings.CRUNCHBASE_API_KEY:
            raise ServiceError("Crunchbase API Key missing configuration.")

        payload = {
            "field_ids": ["identifier", "funding_total", "num_funding_rounds"],
            "query": [
                {
                    "type": "predicate",
                    "field_id": "name",
                    "operator_id": "contains",
                    "values": [query],
                }
            ],
            "limit": 10,
        }

        async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{self.BASE_URL}/searches/organizations",
                params={"user_key": self.settings.CRUNCHBASE_API_KEY},
                json=payload,
            )
            if response.status_code != 200:
                raise ServiceError(f"Crunchbase API Error: {response.status_code}")
            entities = response.json().get("entities", [])

        if not entities:
            raise ServiceError("Crunchbase returned no deals for this topic.")

        return [
            {
                "company": ((entity.get("properties") or {}).get("identifier") or {}).get("value", "Unknown"),
                "amount": float((entity.get("properties") or {}).get("funding_total", 0) or 0),
            }
            for entity in entities
        ]
