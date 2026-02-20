from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_scan_orchestrator
from app.api.routes.radar import ScanRequest
from app.services.scan_logic import ScanOrchestrator

router = APIRouter(tags=["Scanner"])


@router.post("/scan/governance")
async def run_governance_scan(
    request: ScanRequest,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
):
    try:
        return await orchestrator.execute_scan(
            query=request.query,
            mission=request.mission,
            mode="governance",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
