from __future__ import annotations

import httpx

from app.core.config import SEARCH_TIMEOUT_SECONDS
from app.services.search_svc import ServiceError


class GatewayResearchService:
    """Gateway to Research client for UKRI project signals."""

    BASE_URL = "https://gtr.ukri.org/gtr/api"

    async def fetch_projects(self, query: str) -> list[dict]:
        """Fetch project data and normalise it for the scan pipeline."""
        if not query:
            raise ServiceError("GtR query missing.")

        async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT_SECONDS) as client:
            response = await client.get(
                f"{self.BASE_URL}/projects",
                params={"term": query, "page": 1, "size": 10},
            )
            if response.status_code != 200:
                raise ServiceError(f"GtR API Error: {response.status_code}")
            payload = response.json()

        projects = payload.get("project", [])
        if not projects:
            raise ServiceError("GtR returned no projects for this topic.")

        return [
            {
                "title": project.get("title") or project.get("id"),
                "abstract": project.get("abstractText") or project.get("abstract") or "",
                "fund_val": float(project.get("fund", 0) or 0),
                "grantReference": project.get("grantReference", ""),
            }
            for project in projects
        ]
