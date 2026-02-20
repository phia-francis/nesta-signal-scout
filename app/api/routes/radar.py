from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.dependencies import get_scan_orchestrator, get_llm_service
from app.core.exceptions import (
    RateLimitError,
    SearchAPIError,
    LLMServiceError,
    ValidationError,
    SignalScoutError,
)
from app.services.scan_logic import ScanOrchestrator
from app.services.llm_svc import LLMService
from app.storage.scan_storage import get_scan_storage, ScanStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mode", tags=["radar"])


class RadarRequest(BaseModel):
    query: str
    mission: str = "General"


@router.post("/radar")
async def radar_scan(
    body: RadarRequest,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
):
    """
    Streaming Endpoint for Radar Mode (Layered Scan).
    Yields NDJSON lines: { "status": "blip", "blip": {...} }
    """
    return StreamingResponse(
        _radar_stream_generator(body.query, body.mission, orchestrator),
        media_type="application/x-ndjson",
    )


@router.post("/policy")
async def policy_scan(
    body: RadarRequest,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
):
    """
    Streaming Endpoint for Policy Mode.
    """
    return StreamingResponse(
        _policy_stream_generator(body.query, body.mission, orchestrator),
        media_type="application/x-ndjson",
    )


async def _radar_stream_generator(query: str, mission: str, orchestrator: ScanOrchestrator):
    try:
        yield _msg("info", f"Initiating Layered Scan for '{query}'...")

        # 1. Fetch Raw Signals (Layers 1-5)
        raw_signals, related_terms = await orchestrator.fetch_signals(
            topic=query, mission=mission, mode="radar"
        )

        if not raw_signals:
            yield _msg("warning", "No signals found. Try a broader topic.")
            yield _msg("complete", "Scan finished.")
            return

        yield _msg("info", f"Found {len(raw_signals)} potential signals. AI is analysing and rewriting...")

        # -- LLM INTERCEPTION LAYER --
        llm = getattr(orchestrator, 'llm_service', None)
        if llm and getattr(llm, 'client', None):
            # Prepare top 15 results for the LLM
            llm_input = [
                {"id": str(i), "title": s.title, "snippet": s.abstract, "displayLink": s.url or s.source}
                for i, s in enumerate(raw_signals[:15])
            ]

            evaluated_signals = await llm.evaluate_radar_signals(query, llm_input, mission)

            if evaluated_signals:
                evaluated_ids = set()
                count = 0
                for ev in evaluated_signals:
                    try:
                        idx = int(ev.get("id", -1))
                        if 0 <= idx < len(raw_signals):
                            evaluated_ids.add(idx)
                            raw = raw_signals[idx]

                            # Rewrite properties to use AI analytical text
                            raw.abstract = ev.get("summary", raw.abstract)
                            raw.title = ev.get("title", raw.title)

                            scored = orchestrator._score_signal(raw, orchestrator.cutoff_date)
                            if scored:
                                if ev.get("score"):
                                    try:
                                        scored.final_score = float(ev.get("score"))
                                    except ValueError:
                                        pass

                                card = orchestrator._to_signal_card(scored, related_terms=related_terms)
                                data = {"status": "blip", "blip": card.model_dump()}
                                yield json.dumps(data) + "\n"
                                count += 1
                    except (ValueError, TypeError):
                        continue

                # Also yield remaining non-evaluated signals via standard scoring
                remaining = [s for i, s in enumerate(raw_signals) if i not in evaluated_ids]
                for card in orchestrator.process_signals(remaining, mission=mission, related_terms=related_terms):
                    data = {"status": "blip", "blip": card.model_dump()}
                    yield json.dumps(data) + "\n"
                    count += 1

                if count > 0:
                    yield _msg("complete", f"Scan complete. {count} signals analysed.")
                    return

        # -- FALLBACK if LLM unavailable or failed --
        yield _msg("info", "Applying standard scoring...")
        count = 0
        for card in orchestrator.process_signals(raw_signals, mission=mission, related_terms=related_terms):
            data = {"status": "blip", "blip": card.model_dump()}
            yield json.dumps(data) + "\n"
            count += 1

        yield _msg("complete", f"Scan complete. {count} signals visualised.")

    except ValidationError as e:
        logger.warning("Radar validation error: %s", e)
        yield _msg("error", "Invalid request. Please check your query and try again.")
    except RateLimitError as e:
        logger.warning("Radar rate limit hit: %s", e)
        retry_msg = f" Please retry after {e.retry_after}s." if e.retry_after else ""
        yield _msg("error", f"Rate limit exceeded.{retry_msg}")
    except SearchAPIError as e:
        logger.error("Radar search API error: %s", e)
        yield _msg("error", "Search service is temporarily unavailable. Please try again later.")
    except SignalScoutError as e:
        logger.error("Radar scan error: %s", e)
        yield _msg("error", "An error occurred during scanning. Please try again later.")
    except Exception:
        request_id = "radar-scan-failed"
        logger.exception("Radar scan failed. Request ID: %s", request_id)
        yield _msg("error", f"An internal error occurred. Please contact support with ID: {request_id}")


async def _policy_stream_generator(query: str, mission: str, orchestrator: ScanOrchestrator):
    try:
        yield _msg("info", f"Scanning Policy Documents for '{query}'...")

        # 1. Fetch Policy Signals
        # Note: fetch_policy_scan returns Scored Cards directly in v2 logic
        cards = await orchestrator.fetch_policy_scan(query)

        if not cards:
            yield _msg("warning", "No policy documents found.")
            yield _msg("complete", "Scan finished.")
            return

        for card in cards:
            card.mission = mission  # Ensure mission alignment
            data = {"status": "blip", "blip": card.model_dump()}
            yield json.dumps(data) + "\n"

        yield _msg("complete", f"Policy scan complete. {len(cards)} documents found.")

    except ValidationError as e:
        logger.warning("Policy validation error: %s", e)
        yield _msg("error", "Invalid request. Please check your query and try again.")
    except RateLimitError as e:
        logger.warning("Policy rate limit hit: %s", e)
        retry_msg = f" Please retry after {e.retry_after}s." if e.retry_after else ""
        yield _msg("error", f"Rate limit exceeded.{retry_msg}")
    except SearchAPIError as e:
        logger.error("Policy search API error: %s", e)
        yield _msg("error", "Search service is temporarily unavailable. Please try again later.")
    except SignalScoutError as e:
        logger.error("Policy scan error: %s", e)
        yield _msg("error", "An error occurred during scanning. Please try again later.")
    except Exception:
        request_id = "policy-scan-failed"
        logger.exception("Policy scan failed. Request ID: %s", request_id)
        yield _msg("error", f"An internal error occurred. Please contact support with ID: {request_id}")


def _msg(status: str, text: str) -> str:
    """Helper to format a status message for the stream."""
    return json.dumps({"status": status, "msg": text}) + "\n"


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
