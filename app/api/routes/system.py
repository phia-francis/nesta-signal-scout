from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_cluster_service, get_sheet_service
from app.domain.models import UpdateSignalRequest
from app.services.ml_svc import ClusterService
from app.services.search_svc import ServiceError
from app.services.sheet_svc import SheetService

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/saved")
async def get_saved(sheet_service: SheetService = Depends(get_sheet_service)) -> dict[str, Any]:
    """Return all persisted signals from the sheet datastore."""
    try:
        return {"signals": await sheet_service.get_all()}
    except ServiceError as service_error:
        raise HTTPException(
            status_code=503,
            detail="Service unavailable. Please try again later.",
        ) from service_error


@router.post("/update_signal")
async def update_signal(
    request: UpdateSignalRequest,
    sheet_service: SheetService = Depends(get_sheet_service),
) -> dict[str, str]:
    """Update a signal triage status in the datastore."""
    await sheet_service.update_status(request.url, request.status)
    return {"status": "success"}


@router.post("/feedback")
async def feedback(payload: dict[str, Any]) -> dict[str, str]:
    """Accept feedback payload without blocking user flow."""
    _ = payload
    return {"status": "recorded"}


@router.post("/intelligence/cluster")
async def cluster_signals(
    signals: list[dict[str, Any]],
    cluster_service: ClusterService = Depends(get_cluster_service),
) -> list[dict[str, Any]]:
    """Cluster raw signals into narrative groups for UI visualisation."""
    return cluster_service.cluster_signals(signals)
