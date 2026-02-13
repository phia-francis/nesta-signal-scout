from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_cluster_service, get_scan_orchestrator, get_sheet_service
from app.services.cluster_svc import ClusterService
from app.services.scan_logic import ScanOrchestrator
from app.services.sheet_svc import SheetService

router = APIRouter(prefix="/api", tags=["intelligence"])


@router.post("/intelligence/cluster")
async def cluster_signals(
    signals: list[dict[str, Any]],
    cluster_service: ClusterService = Depends(get_cluster_service),
    sheet_service: SheetService = Depends(get_sheet_service),
) -> list[dict[str, Any]]:
    """Group mission-relevant current + historical signals and persist narrative labels."""
    if not signals:
        return []

    mission = str(signals[0].get("mission") or "").strip()
    database_records = await sheet_service.get_all()
    mission_records = [
        record
        for record in database_records
        if str(record.get("Mission") or "").strip() == mission
    ]

    db_signals: list[dict[str, Any]] = [
        {
            "title": record.get("Title", "Untitled"),
            "url": record.get("URL", ""),
            "summary": record.get("Summary", "") or "",
            "source": record.get("Source", "Web"),
            "mission": record.get("Mission", mission or "General"),
            "typology": record.get("Typology", "Unsorted"),
            "score_activity": record.get("Activity Score", 0) or 0,
            "score_attention": record.get("Attention Score", 0) or 0,
            "status": record.get("Status", "New"),
            "mode": record.get("Mode", "Radar"),
        }
        for record in mission_records
    ]

    deduped_by_url: dict[str, dict[str, Any]] = {}
    for signal in [*db_signals, *signals]:
        url = str(signal.get("url") or "").strip()
        if not url:
            continue
        deduped_by_url[url] = signal

    combined_signals = list(deduped_by_url.values())
    if len(combined_signals) < 3:
        return []

    clusters = cluster_service.cluster_signals(combined_signals)

    # Prepare a flat list of signals for persistence, adding narrative_group
    signals_to_save: list[dict[str, Any]] = []
    for cluster in clusters:
        narrative_group = cluster.get("title", "")
        for signal in cluster.get("signals", []):
            payload = dict(signal)
            payload["narrative_group"] = narrative_group
            signals_to_save.append(payload)

    await sheet_service.save_signals_batch(signals_to_save)
    return clusters


@router.post("/mode/intelligence")
async def intelligence_mode(
    payload: dict[str, str],
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
) -> dict[str, object]:
    """Fast intelligence brief returning SignalCard-shaped data."""
    topic = (payload.get("topic") or "").strip()
    cards = await orchestrator.fetch_intelligence_brief(topic)
    return {"status": "success", "data": {"results": [card.model_dump() for card in cards]}}
