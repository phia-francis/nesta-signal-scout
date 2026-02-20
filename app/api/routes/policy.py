from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_scan_orchestrator
from app.domain.models import PolicyRequest
from app.services.scan_logic import ScanOrchestrator

router = APIRouter(prefix="/api", tags=["policy"])


@router.post("/mode/policy")
async def policy_mode(
    request: PolicyRequest,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
) -> dict[str, object]:
    """Run governance scan and return SignalCard payloads."""
    result = await orchestrator.execute_scan(
        query=request.topic, mission=request.mission, mode="governance"
    )
    return {
        "status": "success",
        "data": {
            "results": [card.model_dump() for card in result["signals"]],
        },
    }
