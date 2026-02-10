from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/cron", tags=["cron"])


@router.post("/briefing")
async def create_briefing() -> dict[str, str]:
    """Compatibility endpoint for scheduled briefing jobs."""
    return {"status": "queued"}
