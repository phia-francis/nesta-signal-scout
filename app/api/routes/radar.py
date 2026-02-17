from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.dependencies import get_scan_orchestrator
from app.services.scan_logic import ScanOrchestrator

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

        yield _msg("success", f"Found {len(raw_signals)} potential signals. Scoring...")

        # 2. Score & Yield Cards
        count = 0
        for card in orchestrator.process_signals(raw_signals, mission=mission, related_terms=related_terms):
            # Send the card as a 'blip'
            data = {"status": "blip", "blip": card.model_dump()}
            yield json.dumps(data) + "\n"
            count += 1

        yield _msg("complete", f"Scan complete. {count} signals visualized.")

    except Exception as e:
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

    except Exception as e:
        request_id = "policy-scan-failed"
        logger.exception("Policy scan failed. Request ID: %s", request_id)
        yield _msg("error", f"An internal error occurred. Please contact support with ID: {request_id}")


def _msg(status: str, text: str) -> str:
    """Helper to format a status message for the stream."""
    return json.dumps({"status": status, "msg": text}) + "\n"
