from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.api.dependencies import get_search_service, get_sheet_service
from app.services.search_svc import SearchService
from app.services.sheet_svc import SheetService

router = APIRouter(prefix="/api", tags=["research"])


class StartOpPayload(BaseModel):
    query: str


class ResearchLlmService:
    """Minimal synthesis helper for research mode aggregation."""

    async def generate_signal(self, context: str, system_prompt: str, mode: str) -> dict[str, Any]:
        del system_prompt
        snippets = [line.strip() for line in context.splitlines() if line.strip()]
        return {
            "title": "Research Synthesis",
            "summary": " ".join(snippets[:8])[:500] if snippets else "No synthesis context available.",
            "source": "Web Synthesis",
            "mission": "Research",
            "typology": "Synthesis",
            "score_activity": 0,
            "score_attention": 0,
            "mode": mode,
        }


llm_service = ResearchLlmService()


@router.post("/mode/research")
async def start_research_op(
    payload: StartOpPayload,
    background_tasks: BackgroundTasks,
    search_service: SearchService = Depends(get_search_service),
    sheet_service: SheetService = Depends(get_sheet_service),
) -> list[dict[str, Any]]:
    query = payload.query.strip()
    results = await search_service.search(query, num=10)

    context_text = "\n\n".join(
        [f"Source: {result.get('url') or result.get('link', '')}\nContent: {result.get('snippet', '')}" for result in results]
    )
    bibliography = ", ".join([result.get("url") or result.get("link", "") for result in results if result.get("url") or result.get("link")])

    system_prompt = (
        "You are a strategic analyst. Synthesize these search snippets into ONE comprehensive Signal Card. "
        "Highlight consensus, disagreements, implications, and key unknowns."
    )

    synthesis_signal = await llm_service.generate_signal(
        context=context_text,
        system_prompt=system_prompt,
        mode="Research",
    )
    synthesis_signal["url"] = bibliography

    background_tasks.add_task(sheet_service.save_signals_batch, [synthesis_signal])
    return [synthesis_signal]
