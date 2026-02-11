from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_scan_orchestrator, get_sheet_service
from app.domain.models import RadarRequest
from app.services.scan_logic import ScanOrchestrator
from app.services.search_svc import ServiceError
from app.services.sheet_svc import SheetService

router = APIRouter(prefix="/api", tags=["radar"])


def ndjson_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


@router.post("/mode/radar")
async def radar_scan(
    request: RadarRequest,
    background_tasks: BackgroundTasks,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
    sheet_service: SheetService = Depends(get_sheet_service),
) -> StreamingResponse:
    """Thin controller: validate input, delegate scan orchestration, stream results."""

    effective_topic = (request.topic or "").strip() or (request.query or "").strip()
    if not effective_topic:
        logging.warning("Scan attempted without topic or query.")

        async def invalid_input_generator() -> AsyncGenerator[str, None]:
            yield ndjson_line(
                {
                    "status": "error",
                    "msg": "Please provide a valid topic or search query to start the scan.",
                }
            )

        return StreamingResponse(invalid_input_generator(), media_type="application/x-ndjson")

    request.topic = effective_topic

    async def generator() -> AsyncGenerator[str, None]:
        try:
            mission = request.mission or "All Missions"
            yield ndjson_line({"status": "info", "msg": "Authenticating with Google Sheets..."})
            existing_urls = await sheet_service.get_existing_urls()
            yield ndjson_line(
                {
                    "status": "success",
                    "msg": f"Database Connected. {len(existing_urls)} existing records loaded.",
                }
            )

            raw_signals, related_terms = await orchestrator.fetch_signals(
                request.topic,
                mission=mission,
                mode=request.mode,
                friction_mode=request.friction_mode,
            )
            scored_signals = list(
                orchestrator.process_signals(
                    raw_signals,
                    mission=mission,
                    related_terms=related_terms,
                )
            )

            if not scored_signals:
                yield ndjson_line(
                    {
                        "status": "error",
                        "msg": "No live signals matched the 1 month to 1 year sweet-spot window.",
                    }
                )
                return

            pending_signals: list[dict[str, Any]] = []
            for signal in scored_signals:
                if signal.url in existing_urls:
                    continue
                payload = {"mode": "Radar", **signal.model_dump()}
                pending_signals.append(payload)
                yield ndjson_line({"status": "blip", "blip": payload})

            if pending_signals:
                background_tasks.add_task(sheet_service.queue_signals_for_sync, pending_signals)

            yield ndjson_line({"status": "complete", "msg": "Scan Routine Finished."})
        except ServiceError as service_error:
            logging.error("Service error in radar scan: %s", service_error)
            yield ndjson_line(
                {"status": "error", "msg": f"Live scan failed due to external service error: {service_error}"}
            )
        except ValueError as validation_error:
            logging.warning("Validation error in radar scan: %s", validation_error)
            yield ndjson_line({"status": "error", "msg": str(validation_error)})

    return StreamingResponse(generator(), media_type="application/x-ndjson")
