from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    get_analytics_service,
    get_crunchbase_service,
    get_gateway_service,
    get_search_service,
    get_sheet_service,
    get_taxonomy,
    get_topic_service,
)
from app.core.config import SCAN_RESULT_LIMIT
from app.domain.models import RadarRequest
from app.domain.taxonomy import TaxonomyService
from app.services.analytics_svc import HorizonAnalyticsService
from app.services.crunchbase_svc import CrunchbaseService
from app.services.gtr_svc import GatewayResearchService
from app.services.ml_svc import TopicModellingService
from app.services.scan_logic import _build_search_query
from app.services.search_svc import SearchService, ServiceError
from app.services.sheet_svc import SheetService

router = APIRouter(prefix="/api", tags=["radar"])


def ndjson_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


@router.post("/mode/radar")
async def radar_scan(
    request: RadarRequest,
    search_service: SearchService = Depends(get_search_service),
    sheet_service: SheetService = Depends(get_sheet_service),
    analytics_service: HorizonAnalyticsService = Depends(get_analytics_service),
    gateway_service: GatewayResearchService = Depends(get_gateway_service),
    crunchbase_service: CrunchbaseService = Depends(get_crunchbase_service),
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
            cb_data = await crunchbase_service.fetch_deals(topic)
            mode_message, search_term = _build_search_query(request, taxonomy)
            yield ndjson_line({"status": "info", "msg": mode_message})

            web_results = await search_service.search(search_term, friction_mode=request.friction_mode)

            abstracts = [project.get("abstract", "") for project in gtr_projects if project.get("abstract")]
            refined_keywords = topic_service.perform_lda(abstracts)
            topic_seeds = topic_service.recommend_top2vec_seeds(abstracts)

            activity_score = analytics_service.calculate_activity_score(
                sum(project.get("fund_val", 0) for project in gtr_projects),
                sum(item.get("amount", 0) for item in cb_data),
            )
            niche_results = await search_service.search_niche(topic, friction_mode=request.friction_mode)
            attention_score = analytics_service.calculate_attention_score(
                len(web_results),
                len([item for item in niche_results if item.get("is_niche")]),
            )
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

            for item in web_results[:SCAN_RESULT_LIMIT]:
                if item.get("link") in existing_urls:
                    continue
                signal = {
                    "mode": "Radar",
                    "title": item.get("title", "Untitled Signal"),
                    "summary": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "mission": mission,
                    "score_activity": round(activity_score, 1),
                    "score_attention": round(attention_score, 1),
                    "typology": typology,
                    "sparkline": sparkline,
                    "refined_keywords": refined_keywords,
                    "topic_seeds": topic_seeds,
                    "source": "Google Search",
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
