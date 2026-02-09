from __future__ import annotations

import asyncio
from datetime import datetime
from functools import lru_cache
import json
import random
from typing import Any, AsyncGenerator, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI

from config import Settings
from keywords import CROSS_CUTTING_KEYWORDS, MISSION_KEYWORDS
from models import (
    ChatRequest,
    FeedbackRequest,
    PolicyRequest,
    RadarRequest,
    ResearchRequest,
    UpdateSignalRequest,
)
from services import HorizonAnalyticsService, SearchService, SheetService
from utils import is_date_within_time_filter, parse_source_date

settings = Settings()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

search_svc = SearchService()
sheet_svc = SheetService()
analytics_svc = HorizonAnalyticsService()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def ndjson_line(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


@lru_cache(maxsize=16)
def build_allowed_keywords_menu(mission: str) -> str:
    if not MISSION_KEYWORDS:
        return "Error: Could not load keywords.py variables."
    if any(not terms for terms in MISSION_KEYWORDS.values()):
        return "Error: Could not load keywords.py variables."
    lines: List[str] = []
    if mission != "All Missions":
        terms = MISSION_KEYWORDS.get(mission)
        if not terms:
            return "Error: Could not load keywords.py variables."
        lines.append(f"- {mission}: {', '.join(terms)}")
    else:
        for mission_name, terms in MISSION_KEYWORDS.items():
            if terms:
                lines.append(f"- {mission_name}: {', '.join(terms)}")
    if CROSS_CUTTING_KEYWORDS:
        lines.append(f"- Cross-cutting: {', '.join(CROSS_CUTTING_KEYWORDS)}")
    return "\n".join(lines)


def get_sheet_records(include_rejected: bool = True) -> List[Dict[str, Any]]:
    return asyncio.run(sheet_svc.get_all())


async def upsert_signal(payload: Dict[str, Any]) -> None:
    await sheet_svc.save_signal(payload)


async def _maybe_await(value):
    if asyncio.iscoroutine(value):
        return await value
    return value


def _build_prompt(request: ChatRequest, signal_count: int) -> str:
    menu = build_allowed_keywords_menu(request.mission)
    return (
        f"Generate exactly {signal_count} seeds of weak signals for: {request.message}.\n"
        f"Mission filter: {request.mission}.\n"
        f"Allowed keywords:\n{menu}"
    )


async def chat_endpoint(request: ChatRequest, stream: bool = False) -> Dict[str, Any]:
    signal_count = request.signal_count if request.signal_count > 0 else 5
    prompt = _build_prompt(request, signal_count)
    messages = [
        {"role": "system", "content": "You surface structured weak signals."},
        {"role": "user", "content": prompt},
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "display_signal_card",
                "description": "Return a structured signal card.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "hook": {"type": "string"},
                        "score": {"type": "number"},
                        "score_novelty": {"type": "number"},
                        "score_evidence": {"type": "number"},
                        "score_impact": {"type": "number"},
                        "score_evocativeness": {"type": "number"},
                        "published_date": {"type": "string"},
                    },
                    "required": ["title", "url", "hook", "score"],
                },
            },
        }
    ]

    items: list[dict] = []
    iterations = 0
    while len(items) < signal_count and iterations < 5:
        response = await _maybe_await(
            client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=messages,
                tools=tools,
            )
        )
        tool_calls = response.choices[0].message.tool_calls or []
        if not tool_calls:
            break
        for call in tool_calls:
            if call.function.name != "display_signal_card":
                continue
            payload = json.loads(call.function.arguments)
            score_novelty = float(payload.get("score_novelty") or payload.get("score") or 0)
            score_impact = float(payload.get("score_impact") or payload.get("score") or 0)
            payload["typology"] = analytics_svc.classify_typology(score_novelty, score_impact)
            payload["score_novelty"] = score_novelty
            payload["score_impact"] = score_impact
            payload["growth_metric"] = float(payload.get("growth_metric") or score_novelty)
            payload["magnitude_metric"] = float(payload.get("magnitude_metric") or score_impact)
            payload["sparkline"] = analytics_svc.generate_sparkline()
            published_date = payload.get("published_date")
            if published_date and not is_date_within_time_filter(
                published_date,
                request.time_filter,
                datetime.now(),
            ):
                continue
            payload["published_date"] = (
                parse_source_date(published_date) or published_date or ""
            )
            await _maybe_await(upsert_signal(payload))
            items.append(payload)
            if len(items) >= signal_count:
                break
        iterations += 1

    return {"ui_type": "signal_list", "items": items}


async def stream_chat_generator(query: str, mission: str) -> AsyncGenerator[str, None]:
    results = await search_svc.search(query)
    if not results:
        yield ndjson_line({"status": "error", "msg": "No evidence found"})
        return

    for item in results[:5]:
        novelty = random.uniform(0, 10)
        impact = random.uniform(0, 10)
        typology = analytics_svc.classify_typology(novelty, impact)
        signal = {
            "title": item.get("title", ""),
            "summary": item.get("snippet", ""),
            "url": item.get("link", ""),
            "typology": typology,
            "novelty_score": round(novelty, 1),
            "growth_metric": round(novelty, 1),
            "magnitude_metric": round(impact, 1),
            "sparkline": analytics_svc.generate_sparkline(),
            "mission": mission,
        }
        await sheet_svc.save_signal(signal)
        yield ndjson_line({"status": "blip", "blip": signal})

    yield ndjson_line({"status": "complete"})


@app.post("/api/mode/radar")
async def radar_scan(req: RadarRequest) -> StreamingResponse:
    topic = req.topic or random.choice(MISSION_KEYWORDS.get(req.mission, ["AI"]))
    query = f"{topic} innovation trends"
    return StreamingResponse(stream_chat_generator(query, req.mission), media_type="application/x-ndjson")


@app.post("/api/mode/research")
async def research_scan(req: ResearchRequest) -> StreamingResponse:
    async def generator() -> AsyncGenerator[str, None]:
        yield ndjson_line({"status": "searching"})
        results = await search_svc.search(req.query)
        if not results:
            yield ndjson_line({"status": "error", "msg": "No evidence found"})
            return
        if not settings.OPENAI_API_KEY:
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY missing")
        prompt = (
            "Synthesize a briefing card with Executive Summary, Key Drivers, Strategic Implications, "
            "and Evidence Base from the following sources:\n"
            + "\n".join(item.get("link", "") for item in results[:5])
        )
        response = await _maybe_await(
            client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=[
                    {"role": "system", "content": "You are a Principal Foresight Strategist at Nesta."},
                    {"role": "user", "content": prompt},
                ],
            )
        )
        summary = response.choices[0].message.content or ""
        card = {
            "title": f"Briefing: {req.query}",
            "summary": summary,
            "url": results[0].get("link", ""),
            "typology": "EMERGING",
            "novelty_score": 0,
            "growth_metric": 0,
            "magnitude_metric": 0,
            "sparkline": analytics_svc.generate_sparkline(),
            "mission": req.query,
        }
        yield ndjson_line({"status": "complete", "card": card})

    return StreamingResponse(generator(), media_type="application/x-ndjson")


@app.post("/api/mode/policy")
async def policy_mode(req: PolicyRequest) -> Dict[str, Any]:
    query = f"(site:gov.uk OR site:parliament.uk) {req.topic}"
    results = await search_svc.search(query)
    return {"status": "success", "data": {"results": results}}


@app.get("/api/saved")
async def get_saved() -> Dict[str, Any]:
    return {"signals": await sheet_svc.get_all()}


@app.post("/api/update_signal")
async def update_signal(req: UpdateSignalRequest) -> Dict[str, str]:
    await sheet_svc.update_status(req.url, req.status)
    return {"status": "success"}


@app.post("/api/feedback")
async def feedback(req: FeedbackRequest) -> Dict[str, str]:
    return {"status": "recorded"}


@app.post("/api/chat")
async def chat_endpoint_route(req: ChatRequest) -> Dict[str, Any]:
    return await chat_endpoint(req)
