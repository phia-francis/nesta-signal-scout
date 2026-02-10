from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_cluster_service
from app.services.cluster_svc import ClusterService

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


@router.post("/cluster")
async def cluster_signals(
    signals: list[dict[str, Any]],
    cluster_service: ClusterService = Depends(get_cluster_service),
) -> list[dict[str, Any]]:
    """Group raw signals into narrative clusters for analyst workflows."""
    return cluster_service.cluster_signals(signals)
