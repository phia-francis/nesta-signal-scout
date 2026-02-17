from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

from app.api.dependencies import get_sheet_service, get_search_service
from app.services.sheet_svc import SheetService
from app.services.search_svc import SearchService, ServiceError, RateLimitError

router = APIRouter(prefix="/api", tags=["system"])
logger = logging.getLogger(__name__)


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


@router.get("/test-search")
async def test_search_endpoint(
    search_service: SearchService = Depends(get_search_service)
) -> dict[str, Any]:
    """
    Test endpoint to verify Google Search API is working correctly.
    
    Returns:
        Dict with status, message, and sample results if successful.
    """
    try:
        # Try a simple test query
        test_query = "innovation"
        results = await search_service.search(test_query, num=3)
        
        return {
            "status": "success",
            "message": "Google Search API is working correctly",
            "test_query": test_query,
            "results_count": len(results),
            "sample_results": [
                {
                    "title": item.get("title", "No title"),
                    "link": item.get("link", "No link"),
                    "snippet": item.get("snippet", "No snippet")[:100] + "..." if item.get("snippet") else "No snippet"
                }
                for item in results[:3]
            ]
        }
    except ServiceError as e:
        logger.error(f"Google Search API test failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "error_type": "ServiceError"
        }
    except RateLimitError as e:
        logger.error(f"Rate limit error during test: {e}")
        return {
            "status": "error",
            "message": str(e),
            "error_type": "RateLimitError"
        }
    except Exception as e:
        logger.exception("Unexpected error during search test")
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": "UnexpectedError"
        }

