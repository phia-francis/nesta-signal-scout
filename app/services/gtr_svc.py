from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, cast

import httpx
from dateutil import parser as date_parser

from app.core.resilience import retry_with_backoff

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10.0
HEADERS = {"Accept": "application/vnd.rcuk.gtr.json-v7"}
PAGE_SIZE = 10


class GatewayResearchService:
    """Gateway to Research client for UKRI project signals."""

    BASE_URL = "https://gtr.ukri.org/gtr/api"

    @staticmethod
    def _parse_project_date(project: dict[str, Any]) -> datetime | None:
        for key in ("start", "startDate", "start_date", "firstAuthorised"):
            value = project.get(key)
            if value:
                try:
                    parsed = cast(datetime, date_parser.parse(str(value)))
                    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError, date_parser.ParserError):
                    continue
        return None

    @retry_with_backoff(retries=3, delay=1.0)
    async def fetch_projects(self, query: str, min_start_date: datetime) -> list[dict[str, Any]]:
        """Fetch project data and normalise it for the scan pipeline."""
        if not query:
            logger.warning("GtR query missing.")
            return []

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.get(
                    f"{self.BASE_URL}/projects",
                    params={"term": query, "page": 1, "size": PAGE_SIZE},
                    headers=HEADERS,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("GtR API returned status for query '%s': %s", query, exc.response.status_code)
            raise
        except httpx.HTTPError as exc:
            logger.error("GtR request failed for query '%s': %s", query, exc)
            return []

        try:
            payload = response.json()
        except json.JSONDecodeError:
            logger.error(
                "GtR API returned invalid JSON for query '%s'. Raw body: %s",
                query,
                response.text,
            )
            return []

        projects = payload.get("project", []) if isinstance(payload, dict) else []
        if not projects:
            return []

        normalised_projects: list[dict[str, Any]] = []
        for project in projects:
            project_date = self._parse_project_date(project)
            if project_date and project_date < min_start_date:
                continue

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
                    "start_date": project_date,
                }
            )

        return normalised_projects
