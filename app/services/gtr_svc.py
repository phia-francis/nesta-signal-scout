from __future__ import annotations

import logging

import httpx


logger = logging.getLogger(__name__)


class GatewayResearchService:
    """Gateway to Research client for UKRI project signals."""

    BASE_URL = "https://gtr.ukri.org/gtr/api"

    async def fetch_projects(self, query: str) -> list[dict]:
        """Fetch project data and normalise it for the scan pipeline."""
        if not query:
            logger.warning("GtR query missing.")
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/projects",
                    params={"term": query, "page": 1, "size": 10},
                    headers={"Accept": "application/vnd.rcuk.gtr.json-v7"},
                )
        except httpx.HTTPError as exc:
            logger.error("GtR request failed for query '%s': %s", query, exc)
            return []

        if response.status_code != 200:
            logger.error(
                "GtR API returned non-200 status for query '%s': %s",
                query,
                response.status_code,
            )
            return []

        try:
            payload = response.json()
        except ValueError:
            logger.error(
                "GtR API returned invalid JSON for query '%s'. Raw body: %s",
                query,
                response.text,
            )
            return []

        projects = payload.get("project", [])
        if not projects:
            return []

        normalised_projects: list[dict] = []
        for project in projects:
            try:
                fund_val = float(project.get("fund", 0) or 0)
            except (TypeError, ValueError):
                fund_val = 0.0

            normalised_projects.append(
                {
                    "title": project.get("title") or project.get("id"),
                    "abstract": project.get("abstractText") or project.get("abstract") or "",
                    "fund_val": fund_val,
                    "grantReference": project.get("grantReference", ""),
                }
            )

        return normalised_projects
