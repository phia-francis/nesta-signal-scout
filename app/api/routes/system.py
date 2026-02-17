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
            # We assume the row exists, but we might not have the full object here.
            # Ideally, the frontend sends the full object, but for now we just
            # update the status column.
            pass

        return {"status": "success", "message": f"Signal marked as {payload.status}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
