from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    get_analytics_service,
    get_openalex_service,
    get_gateway_service,
    get_sheet_service,
    get_taxonomy,
    get_topic_service,
)
from app.core.config import SCAN_RESULT_LIMIT
from app.domain.models import RadarRequest
from app.domain.taxonomy import TaxonomyService
from app.services.analytics_svc import HorizonAnalyticsService
from app.services.openalex_svc import OpenAlexService
from app.services.gtr_svc import GatewayResearchService
from app.services.ml_svc import TopicModellingService
from app.services.scan_logic import _build_search_query
from app.services.search_svc import ServiceError
from app.services.sheet_svc import SheetService

router = APIRouter(prefix="/api", tags=["radar"])


def ndjson_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


@router.post("/mode/radar")
async def radar_scan(
    request: RadarRequest,
    sheet_service: SheetService = Depends(get_sheet_service),
    analytics_service: HorizonAnalyticsService = Depends(get_analytics_service),
    gateway_service: GatewayResearchService = Depends(get_gateway_service),
    openalex_service: OpenAlexService = Depends(get_openalex_service),
    topic_service: TopicModellingService = Depends(get_topic_service),
    taxonomy: TaxonomyService = Depends(get_taxonomy),
) -> StreamingResponse:
    """Run the radar scan and stream NDJSON updates for responsive UI behaviour."""

    async def generator() -> AsyncGenerator[str, None]:
        try:
            topic = request.topic or "innovation"
            mission = request.mission or "All Missions"

            yield ndjson_line({"status": "info", "msg": "Authenticating with Google Sheets..."})
            existing_urls = await sheet_service.get_existing_urls()
            yield ndjson_line(
                {
                    "status": "success",
                    "msg": f"Database Connected. {len(existing_urls)} existing records loaded.",
                }
            )

            gtr_projects = await gateway_service.fetch_projects(topic)
            openalex_works = await openalex_service.search_works(topic)
            mode_message, _ = _build_search_query(request, taxonomy)
            yield ndjson_line({"status": "info", "msg": mode_message})


            abstracts = [project.get("abstract", "") for project in gtr_projects if project.get("abstract")]
            refined_keywords = topic_service.perform_lda(abstracts)
            topic_seeds = topic_service.recommend_top2vec_seeds(abstracts)

            activity_score = analytics_service.calculate_activity_score(
                sum(project.get("fund_val", 0) for project in gtr_projects),
                sum(work.get("score", 0) for work in openalex_works),
            )
            max_citations = max((work.get("score", 0) for work in openalex_works), default=0)
            attention_score = min(10.0, max_citations / 100) if max_citations else 0.0
            typology = analytics_service.classify_sweet_spot(activity_score, attention_score)
            sparkline = analytics_service.generate_sparkline(activity_score, attention_score)

            for project in gtr_projects[:SCAN_RESULT_LIMIT]:
                signal = {
                    "mode": "Radar",
                    "title": project.get("title", f"GtR: {topic}"),
                    "summary": project.get("abstract", ""),
                    "url": f"https://gtr.ukri.org/projects?ref={project.get('grantReference') or project.get('title', '')}",
                    "mission": mission,
                    "score_activity": round(activity_score, 1),
                    "score_attention": round(attention_score, 1),
                    "typology": typology,
                    "sparkline": sparkline,
                    "refined_keywords": refined_keywords,
                    "topic_seeds": topic_seeds,
                    "source": "UKRI GtR",
                }
                if signal["url"] in existing_urls:
                    continue
                await sheet_service.save_signal(signal, existing_urls)
                yield ndjson_line({"status": "blip", "blip": signal})

            for work in openalex_works[:SCAN_RESULT_LIMIT]:
                if work.get("url") in existing_urls:
                    continue
                work_attention = min(10.0, (work.get("score", 0) / 100))
                signal = {
                    "mode": "Radar",
                    "title": work.get("title", "Untitled Signal"),
                    "summary": work.get("summary", ""),
                    "url": work.get("url", ""),
                    "mission": mission,
                    "score_activity": round(activity_score, 1),
                    "score_attention": round(work_attention, 1),
                    "typology": "Global Research",
                    "sparkline": sparkline,
                    "refined_keywords": refined_keywords,
                    "topic_seeds": topic_seeds,
                    "source": "OpenAlex",
                }
                await sheet_service.save_signal(signal, existing_urls)
                yield ndjson_line({"status": "blip", "blip": signal})

            yield ndjson_line({"status": "complete", "msg": "Scan Routine Finished."})
        except ServiceError as service_error:
            logging.error("Service error in radar scan: %s", service_error)
            yield ndjson_line(
                {"status": "error", "msg": "Service unavailable. Please try again later."}
            )

    return StreamingResponse(generator(), media_type="application/x-ndjson")
