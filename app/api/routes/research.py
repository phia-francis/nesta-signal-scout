from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_scan_orchestrator, get_sheet_service
from app.domain.models import ResearchRequest
from app.services.scan_logic import ScanOrchestrator
from app.services.search_svc import ServiceError
from app.services.sheet_svc import SheetService

router = APIRouter(prefix="/api", tags=["research"])


def ndjson_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


@router.post("/mode/research")
async def research_scan(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
    sheet_service: SheetService = Depends(get_sheet_service),
) -> StreamingResponse:
    """Run research deep dive and stream SignalCard payloads."""

    async def generator() -> AsyncGenerator[str, None]:
        try:
            query = (request.query or "").strip()
            if not query:
                yield ndjson_line({"status": "error", "msg": "Please provide a research query."})
                return

            yield ndjson_line({"status": "searching", "msg": f"Deep researching '{query}'..."})
            existing_urls = await sheet_service.get_existing_urls()
            cards = await orchestrator.fetch_research_deep_dive(query)

            pending_signals: list[dict[str, Any]] = []
            for card in cards:
                if card.url in existing_urls:
                    continue
                payload = {"mode": "Research", **card.model_dump()}
                pending_signals.append(payload)
                yield ndjson_line({"status": "blip", "blip": payload})

            if pending_signals:
                background_tasks.add_task(sheet_service.queue_signals_for_sync, pending_signals)

            yield ndjson_line({"status": "complete"})
        except ServiceError as service_error:
            logging.error("Service error in research scan: %s", service_error)
            yield ndjson_line({"status": "error", "msg": "Service unavailable. Please try again later."})
        except ValueError as validation_error:
            logging.warning("Validation error in research scan: %s", validation_error)
            yield ndjson_line({"status": "error", "msg": str(validation_error)})

    return StreamingResponse(generator(), media_type="application/x-ndjson")
