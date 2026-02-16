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
    """Run policy-specific scan and return SignalCard payloads."""
    cards = await orchestrator.fetch_policy_scan(request.topic)
    return {
        "status": "success",
        "data": {
            "results": [card.model_dump() for card in cards],
        },
    }
