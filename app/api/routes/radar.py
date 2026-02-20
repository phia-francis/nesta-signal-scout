from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_scan_orchestrator, get_llm_service, get_sheet_service
from app.core.exceptions import LLMServiceError
from app.services.scan_logic import ScanOrchestrator
from app.services.llm_svc import LLMService
from app.services.sheet_svc import SheetService
from app.storage.scan_storage import get_scan_storage, ScanStorage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scanner"])


class ScanRequest(BaseModel):
    query: str
    mission: str = "A Healthy Life"


@router.post("/scan/radar")
async def run_radar_scan(
    request: ScanRequest,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
    sheet_service: SheetService = Depends(get_sheet_service),
):
    try:
        result = await orchestrator.execute_scan(
            query=request.query,
            mission=request.mission,
            mode="radar",
        )
        if result.get("signals"):
            try:
                await sheet_service.save_signals_batch(
                    [s.model_dump() for s in result["signals"]]
                )
            except Exception as save_err:
                logger.warning("Failed to persist radar signals to Sheets: %s", save_err)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ClusterRequest(BaseModel):
    """Request body for clustering signals."""
    signals: list[dict[str, Any]]


@router.post("/cluster")
async def cluster_signals(
    body: ClusterRequest,
    llm_service: LLMService = Depends(get_llm_service),
    storage: ScanStorage = Depends(get_scan_storage),
):
    """
    Cluster signals into 3-5 themes using LLM analysis.
    """
    try:
        if not body.signals or len(body.signals) == 0:
            return {"themes": [], "error": "No signals provided"}
        
        logger.info(f"Clustering {len(body.signals)} signals")
        
        # Call LLM service to cluster
        result = await llm_service.cluster_signals(body.signals)
        themes = result.get('themes', [])
        
        logger.info(f"Clustering complete: {len(themes)} themes found")
        
        # Save scan with themes to storage
        query = body.signals[0].get('title', 'Unknown query') if body.signals else 'Unknown query'
        mode = 'cluster'
        
        try:
            scan_id = storage.save_scan(
                query=query,
                mode=mode,
                signals=body.signals,
                themes=themes
            )
            logger.info(f"Saved scan {scan_id} with {len(themes)} themes")
            
            return {
                "scan_id": scan_id,
                "themes": themes
            }
        except Exception as save_error:
            logger.error(f"Failed to save scan: {save_error}")
            return {
                "themes": themes,
                "warning": "Failed to save scan to storage"
            }
        
    except LLMServiceError:
        logger.exception("Clustering LLM call failed")
        return {"themes": [], "error": "LLM clustering failed due to an internal error"}
    except Exception as e:
        logger.exception("Clustering failed")
        return {"themes": [], "error": "Clustering failed due to an internal error"}


@router.get("/scan/{scan_id}")
async def get_scan(
    scan_id: str,
    storage: ScanStorage = Depends(get_scan_storage),
):
    """
    Retrieve a saved scan by ID.
    """
    try:
        scan_data = storage.get_scan(scan_id)
        
        if not scan_data:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found or has expired")
        return scan_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to retrieve scan {scan_id}")
        # FIXED: Removed detail=str(e), replaced with generic message
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/scans")
async def list_scans(
    limit: int = 50,
    storage: ScanStorage = Depends(get_scan_storage),
):
    """
    List recent scans.
    """
    try:
        scans = storage.list_scans(limit=limit)
        return {"scans": scans, "count": len(scans)}
    except Exception as e:
        logger.exception("Failed to list scans")
        # FIXED: Removed detail=str(e), replaced with generic message
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.delete("/scan/{scan_id}")
async def delete_scan(
    scan_id: str,
    storage: ScanStorage = Depends(get_scan_storage),
):
    """
    Delete a scan.
    """
    try:
        success = storage.delete_scan(scan_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
        
        return {"message": f"Scan {scan_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete scan {scan_id}")
        # FIXED: Removed detail=str(e), replaced with generic message
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/cleanup")
async def cleanup_old_scans(
    days: int = 30,
    storage: ScanStorage = Depends(get_scan_storage),
):
    """
    Cleanup scans older than specified days.
    """
    try:
        deleted_count = storage.cleanup_old_scans(days=days)
        return {
            "message": f"Deleted {deleted_count} scans older than {days} days",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.exception("Failed to cleanup old scans")
        # FIXED: Removed detail=str(e), replaced with generic message
        raise HTTPException(status_code=500, detail="Internal Server Error")
