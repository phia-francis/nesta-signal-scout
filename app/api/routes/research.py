from __future__ import annotations

import json
import logging
import random
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_analytics_service, get_search_service, get_sheet_service
from app.domain.models import ResearchRequest
from app.services.analytics_svc import HorizonAnalyticsService
from app.services.search_svc import SearchService, ServiceError
from app.services.sheet_svc import SheetService

router = APIRouter(prefix="/api", tags=["research"])


def ndjson_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


@router.post("/mode/research")
async def research_scan(
    request: ResearchRequest,
    search_service: SearchService = Depends(get_search_service),
    sheet_service: SheetService = Depends(get_sheet_service),
    analytics_service: HorizonAnalyticsService = Depends(get_analytics_service),
) -> StreamingResponse:
    """Run targeted research scan and stream progress for user feedback."""

    async def generator() -> AsyncGenerator[str, None]:
        try:
            yield ndjson_line(
                {"status": "searching", "msg": f"Deep researching '{request.query}'..."}
            )
            existing_urls = await sheet_service.get_existing_urls()
            results = await search_service.search(f"{request.query} whitepaper report pdf", num=5)

            for item in results:
                activity = random.uniform(7, 10)
                attention = random.uniform(2, 6)
                signal = {
                    "mode": "Research",
                    "title": item.get("title", "Untitled"),
                    "summary": item.get("snippet", "No summary"),
                    "url": item.get("link", "#"),
                    "mission": "Targeted Research",
                    "typology": "Evidence",
                    "score_activity": round(activity, 1),
                    "score_attention": round(attention, 1),
                    "sparkline": analytics_service.generate_sparkline(activity, attention),
                    "source": "Google Search",
                }
                await sheet_service.save_signal(signal, existing_urls)
                yield ndjson_line({"status": "blip", "blip": signal})

            yield ndjson_line({"status": "complete"})
        except ServiceError as service_error:
            logging.error("Service error in research scan: %s", service_error)
            yield ndjson_line(
                {"status": "error", "msg": "Service unavailable. Please try again later."}
            )

    return StreamingResponse(generator(), media_type="application/x-ndjson")
