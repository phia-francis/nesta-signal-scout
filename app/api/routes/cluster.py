from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_llm_service, get_sheet_service
from app.services.llm_svc import LLMService
from app.services.sheet_svc import SheetService

logger = logging.getLogger(__name__)

router = APIRouter()


class ClusterAnalysisRequest(BaseModel):
    clusters: list[dict[str, Any]]
    mission: str = "A Healthy Life"


@router.post("/cluster/analyze")
async def generate_cluster_analysis(
    request: ClusterAnalysisRequest,
    llm_service: LLMService = Depends(get_llm_service),
    sheet_service: SheetService = Depends(get_sheet_service),
):
    try:
        insights = await llm_service.analyze_trend_clusters(request.clusters, request.mission)
        for insight in insights:
            await sheet_service.save_trend_analysis(
                cluster_name=insight.get("cluster_name", "Unknown"),
                analysis_text=insight.get("trend_summary", ""),
                strength=insight.get("strength", "Moderate"),
            )
        return {"status": "success", "insights": insights}
    except Exception:
        logger.exception("Failed to generate cluster analysis")
        raise HTTPException(status_code=500, detail="Failed to generate cluster analysis")
