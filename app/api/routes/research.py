"""
Research mode route with proper LLM synthesis.
FIXED: Now aggregates many sources into ONE comprehensive Signal Card.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.dependencies import get_llm_service, get_scan_orchestrator, get_sheet_service
from app.domain.models import ResearchRequest, SignalCard
from app.services.llm_svc import LLMService
from app.services.scan_logic import ScanOrchestrator
from app.services.sheet_svc import SheetService

router = APIRouter(prefix="/api", tags=["research"])
logger = logging.getLogger(__name__)

# Number of sources to aggregate for synthesis
NUM_SOURCES_FOR_SYNTHESIS = 12
MAX_CONTEXT_LENGTH = 8000  # Characters


@router.post("/mode/research")
async def research_mode(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
    sheet_service: SheetService = Depends(get_sheet_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> dict[str, object]:
    """
    Research mode: Aggregate multiple sources → synthesise into ONE comprehensive Signal Card.

    Flow:
    1. Fetch signals from all sources (Google, OpenAlex, GtR)
    2. Build aggregated context from top N sources
    3. Use LLM to synthesise one comprehensive card
    4. Persist to database
    5. Return single-item list with synthesis

    Returns:
        JSON response with single synthesised Signal Card
    """
    query = (request.query or "").strip()
    if not query:
        return {
            "status": "error",
            "message": "Query is required for research mode",
            "data": {"results": []},
        }

    try:
        # Step 1: Fetch raw signals from all sources
        raw_signals, _ = await orchestrator.fetch_signals(
            query,
            mission="Research",
            mode="research",
            friction_mode=False,
        )

        if not raw_signals:
            logger.warning("No signals found for research query: %s", query)
            return {
                "status": "success",
                "message": "No research signals found",
                "data": {"results": []},
            }

        # Step 2: Build aggregated context (limit to top N sources)
        sources_for_synthesis = raw_signals[:NUM_SOURCES_FOR_SYNTHESIS]
        context_parts: list[str] = []
        source_urls: list[str] = []

        for idx, signal in enumerate(sources_for_synthesis, 1):
            source_urls.append(signal.url)
            snippet = f"[Source {idx}] {signal.source}\n"
            snippet += f"Title: {signal.title}\n"
            snippet += f"URL: {signal.url}\n"
            snippet += f"Abstract: {signal.abstract[:600]}\n"  # Limit length per source
            context_parts.append(snippet)

        # Combine context with length limit
        full_context = "\n\n".join(context_parts)
        if len(full_context) > MAX_CONTEXT_LENGTH:
            full_context = full_context[:MAX_CONTEXT_LENGTH] + "\n\n[Context truncated due to length...]"

        # Step 3: Generate LLM synthesis
        system_prompt = """You are an expert research analyst for Nesta, a UK innovation foundation.

Your task is to synthesise multiple research sources into ONE comprehensive Signal Card that:
- Identifies the core innovation or trend across all sources
- Highlights key insights, patterns, and conflicts
- Assesses the maturity and attention levels
- Uses clear, policy-relevant language

Format your response as JSON with these exact fields:
- title: Clear headline (max 120 chars)
- summary: Comprehensive synthesis (400-600 chars)
- typology: One of "Nascent", "Hidden Gem", "Hype", "Established"
- mission: "Research"
- score_activity: Research/funding activity level (0-10)
- score_attention: Public/media attention level (0-10)"""

        synthesis = await llm_service.generate_signal(
            context=full_context,
            system_prompt=system_prompt,
            mode="Research",
        )

        # Step 4: Add bibliography and metadata
        synthesis["url"] = ", ".join(source_urls[:5])  # First 5 URLs
        synthesis["status"] = "New"
        synthesis["mode"] = "Research"

        # Convert to SignalCard model for validation
        signal_card = SignalCard(
            title=synthesis["title"],
            url=synthesis["url"],
            summary=synthesis["summary"],
            source=synthesis.get("source", "AI Synthesis"),
            mission=synthesis.get("mission", "Research"),
            date="",  # Synthesis doesn't have a single date
            score_activity=synthesis.get("score_activity", 0),
            score_attention=synthesis.get("score_attention", 0),
            score_recency=0.0,
            final_score=0.0,
            typology=synthesis.get("typology", "Nascent"),
            is_novel=False,
            sparkline=[],
            related_keywords=[],
        )

        # Step 5: Persist to database (background task)
        background_tasks.add_task(sheet_service.save_signals_batch, [synthesis])

        logger.info("Research synthesis completed for query: %s", query)

        return {
            "status": "success",
            "message": "Research synthesis completed",
            "data": {"results": [signal_card.model_dump()]},
        }

    except Exception as e:
        logger.error("Research mode failed for query '%s': %s", query, e, exc_info=True)
        return {
            "status": "error",
            "message": f"Research synthesis failed: {str(e)}",
            "data": {"results": []},
        }
