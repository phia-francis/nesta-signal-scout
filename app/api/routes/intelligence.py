from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from utils import normalize_url_for_deduplication
from app.api.dependencies import (
    get_cluster_service,
    get_scan_orchestrator,
    get_search_service,
    get_sheet_service,
)
from app.services.cluster_svc import ClusterService
from app.services.scan_logic import ScanOrchestrator
from app.services.search_svc import SearchService
from app.services.sheet_svc import SheetService

router = APIRouter(prefix="/api", tags=["intelligence"])


class StartOpPayload(BaseModel):
    query: str


class IntelligenceLlmService:
    """Lightweight synthesis helpers for search result shaping."""

    async def generate_signal(self, context: str, system_prompt: str, mode: str) -> dict[str, Any]:
        del system_prompt
        snippets = [line.strip() for line in context.splitlines() if line.strip()]
        summary = " ".join(snippets[:6])[:500] if snippets else "No synthesis context available."
        return {
            "title": "Research Synthesis",
            "summary": summary,
            "source": "Web Synthesis",
            "mission": "Research",
            "typology": "Synthesis",
            "score_activity": 0,
            "score_attention": 0,
            "mode": mode.title(),
        }

    async def process_single_result(self, result: dict[str, Any], mode: str) -> dict[str, Any] | None:
        url = str(result.get("url") or "").strip()
        if not url:
            return None
        return {
            "title": result.get("title") or "Untitled",
            "url": url,
            "summary": (result.get("snippet") or "")[:500],
            "source": "Web",
            "mission": "General",
            "typology": "Unsorted",
            "score_activity": 0,
            "score_attention": 0,
            "mode": mode.title(),
        }


llm_service = IntelligenceLlmService()


@router.post("/intelligence/cluster")
async def cluster_signals(
    signals: list[dict[str, Any]],
    background_tasks: BackgroundTasks,
    cluster_service: ClusterService = Depends(get_cluster_service),
    sheet_service: SheetService = Depends(get_sheet_service),
) -> list[dict[str, Any]]:
    """Group mission-relevant current + historical signals and persist narrative labels."""
    if not signals:
        return []

    mission = str(signals[0].get("mission") or "").strip()
    # TODO: Refactor SheetService to support server-side filtering (e.g. get_rows_by_mission) to avoid OOM on large datasets.
    database_records = await sheet_service.get_all()
    mission_records = [
        record
        for record in database_records
        if str(record.get("Mission") or "").strip() == mission
    ]

    db_signals: list[dict[str, Any]] = [
        {
            "title": record.get("Title", "Untitled"),
            "url": record.get("URL", ""),
            "summary": record.get("Summary", "") or "",
            "source": record.get("Source", "Web"),
            "mission": record.get("Mission", mission or "General"),
            "typology": record.get("Typology", "Unsorted"),
            "score_activity": record.get("Activity Score", 0) or 0,
            "score_attention": record.get("Attention Score", 0) or 0,
            "status": record.get("Status", "New"),
            "mode": record.get("Mode", "Radar"),
        }
        for record in mission_records
    ]

    # Deduplicate by normalized URL
    deduped_by_url: dict[str, dict[str, Any]] = {}
    for signal in [*db_signals, *signals]:
        url = str(signal.get("url") or "").strip()
        if not url:
            continue
        # Use normalized URL as key for better deduplication
        normalized = normalize_url_for_deduplication(url)
        if normalized:
            deduped_by_url[normalized] = signal

    combined_signals = list(deduped_by_url.values())
    if len(combined_signals) < 3:
        return []

    clusters = cluster_service.cluster_signals(combined_signals)

    # Prepare a flat list of signals for persistence, adding narrative_group
    signals_to_save: list[dict[str, Any]] = []
    for cluster in clusters:
        narrative_group = cluster.get("title", "")
        for signal in cluster.get("signals", []):
            payload = dict(signal)
            payload["narrative_group"] = narrative_group
            signals_to_save.append(payload)

    background_tasks.add_task(sheet_service.save_signals_batch, signals_to_save)
    return clusters


@router.post("/mode/intelligence")
async def intelligence_mode(
    payload: dict[str, str],
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
) -> dict[str, object]:
    """Fast intelligence brief returning SignalCard-shaped data."""
    topic = (payload.get("topic") or "").strip()
    cards = await orchestrator.fetch_intelligence_brief(topic)
    return {"status": "success", "data": {"results": [card.model_dump() for card in cards]}}


@router.post("/mode/{mode}")
async def generate_signals(
    mode: str,
    payload: StartOpPayload,
    background_tasks: BackgroundTasks,
    search_service: SearchService = Depends(get_search_service),
    sheet_service: SheetService = Depends(get_sheet_service),
) -> list[dict[str, Any]]:
    raw_results = await search_service.search(payload.query, num=10)
    normalized_results = [
        {
            "title": result.get("title", "Untitled"),
            "url": result.get("url") or result.get("link") or "",
            "snippet": result.get("snippet") or result.get("summary") or "",
        }
        for result in raw_results
    ]

    generated_signals: list[dict[str, Any]] = []
    if mode == "research":
        combined_context = "\n\n".join(
            [f"Source ({result['url']}): {result['snippet']}" for result in normalized_results if result["url"]]
        )
        all_urls = ", ".join([result["url"] for result in normalized_results if result["url"]])

        system_prompt = (
            "You are an expert analyst. Synthesize the provided search snippets into ONE comprehensive "
            "Signal Card. Aggregate perspectives and conflicts. "
            "The 'URL' field must contain the primary source, but mention others in the text."
        )

        synthesis = await llm_service.generate_signal(
            context=combined_context,
            system_prompt=system_prompt,
            mode="research",
        )
        synthesis["url"] = all_urls
        generated_signals.append(synthesis)
    else:
        for result in normalized_results:
            signal = await llm_service.process_single_result(result, mode=mode)
            if signal:
                generated_signals.append(signal)

    if generated_signals:
        background_tasks.add_task(sheet_service.save_signals_batch, generated_signals)

    return generated_signals
