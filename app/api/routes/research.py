from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_scan_orchestrator, get_sheet_service
from app.api.routes.radar import ScanRequest
from app.services.scan_logic import ScanOrchestrator
from app.services.sheet_svc import SheetService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scanner"])


@router.post("/scan/research")
async def run_research_scan(
    request: ScanRequest,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
    sheet_service: SheetService = Depends(get_sheet_service),
):
    try:
        result = await orchestrator.execute_scan(
            query=request.query,
            mission=request.mission,
            mode="research",
        )
        if result.get("signals"):
            try:
                await sheet_service.save_signals_batch(
                    [s.model_dump() for s in result["signals"]]
                )
            except Exception as save_err:
                logger.warning("Failed to persist research signals to Sheets: %s", save_err)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
