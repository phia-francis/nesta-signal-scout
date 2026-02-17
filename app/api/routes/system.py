from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

from app.api.dependencies import get_sheet_service
from app.services.sheet_svc import SheetService

router = APIRouter(prefix="/api", tags=["system"])


class UpdateStatusRequest(BaseModel):
    url: str
    status: str  # e.g., "Starred", "Archived", "Read"


@router.get("/saved")
async def get_saved_signals(
    sheet_service: SheetService = Depends(get_sheet_service)
) -> list[dict[str, Any]]:
    """Fetch all signals from the database."""
    return await sheet_service.get_all()


@router.post("/saved")
async def update_signal_status(
    payload: UpdateStatusRequest,
    sheet_service: SheetService = Depends(get_sheet_service)
):
    """
    Update the status of a signal (e.g. Star/Archive).
    """
    if not payload.url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        await sheet_service.update_status(payload.url, payload.status)

        # If 'Starred', also add to watchlist tab for safety
        if payload.status == "Starred":
            # Check if the signal was actually updated by the previous call to update_status.
            # If not, it means it's a new signal that needs to be persisted.
            existing_signal = await sheet_service.get_signal_by_url(payload.url)
            if not existing_signal:
                # Create a minimal RawSignal object for persistence.
                # This addresses the P1 issue of new starred signals not being persisted.
                from datetime import datetime, timezone
                from app.domain.models import RawSignal
                minimal_signal = RawSignal(
                    url=payload.url,
                    status=payload.status,
                    title=f"Starred: {payload.url}",
                    summary="Signal starred by user, full details not available at time of starring.",
                    source="User Action",
                    mission="General",
                    date=datetime.now(timezone.utc),
                    raw_score=0.0,
                    metadata={"starred_from_frontend": True},
                    is_novel=False
                )
                await sheet_service.add_signal(minimal_signal)

        return {"status": "success", "message": f"Signal marked as {payload.status}"}
    except Exception as e:
        logger.exception("Failed to update signal status for URL: %s", payload.url)
        raise HTTPException(status_code=500, detail="An internal error occurred while updating signal status.")
