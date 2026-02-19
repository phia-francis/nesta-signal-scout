from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.dependencies import get_llm_service, get_scan_orchestrator, get_sheet_service
from app.domain.models import ResearchRequest
from app.services.llm_svc import LLMService
from app.services.scan_logic import ScanOrchestrator
from app.services.sheet_svc import SheetService

router = APIRouter(prefix="/api", tags=["research"])

NUM_SIGNALS_FOR_SYNTHESIS = 8


@router.post("/mode/research")
async def research_scan(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
    sheet_service: SheetService = Depends(get_sheet_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    query = (request.query or "").strip()

    # 1. Gather raw context (Search + OpenAlex)
    raw_signals, _ = await orchestrator.fetch_signals(query, mission="Research", mode="research")

    if not raw_signals:
        return []

    # 2. Synthesize (Many Sources -> One Signal)
    context_text = "\n\n".join([f"Source: {s.url}\nSummary: {s.abstract}" for s in raw_signals[:NUM_SIGNALS_FOR_SYNTHESIS]])

    system_prompt = (
        "You are a strategic analyst. Synthesize the provided search snippets into ONE comprehensive "
        "Signal Card. This signal must aggregate all perspectives, conflicts, and data points found."
    )

    synthesis = await llm_service.generate_signal(
        context=context_text,
        system_prompt=system_prompt,
        mode="Research",
    )

    # 3. Create descriptive title and attach real sources
    synthesis["title"] = f"{query.title()}: A Research Synthesis"
    synthesis["sources"] = [
        {"title": s.title, "url": s.url}
        for s in raw_signals[:NUM_SIGNALS_FOR_SYNTHESIS]
        if s.url
    ]
    synthesis["url"] = f"synthesis:{uuid.uuid4().hex[:12]}"
    background_tasks.add_task(sheet_service.save_signals_batch, [synthesis])

    return [synthesis]
