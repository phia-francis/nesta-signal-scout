from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_cluster_service, get_scan_orchestrator
from app.services.cluster_svc import ClusterService
from app.services.scan_logic import ScanOrchestrator

router = APIRouter(prefix="/api", tags=["intelligence"])


@router.post("/intelligence/cluster")
async def cluster_signals(
    signals: list[dict[str, Any]],
    cluster_service: ClusterService = Depends(get_cluster_service),
) -> list[dict[str, Any]]:
    """Group raw signals into narrative clusters for analyst workflows."""
    return cluster_service.cluster_signals(signals)


@router.post("/mode/intelligence")
async def intelligence_mode(
    payload: dict[str, str],
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
) -> dict[str, object]:
    """Fast intelligence brief returning SignalCard-shaped data."""
    topic = (payload.get("topic") or "").strip()
    cards = await orchestrator.fetch_intelligence_brief(topic)
    return {"status": "success", "data": {"results": [card.model_dump() for card in cards]}}
