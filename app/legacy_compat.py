from __future__ import annotations

import asyncio
import json
from datetime import datetime
from functools import lru_cache
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel

from keywords import CROSS_CUTTING_KEYWORDS, MISSION_KEYWORDS
from utils import is_date_within_time_filter, parse_source_date


@lru_cache(maxsize=32)
def build_allowed_keywords_menu(mission: str) -> str:
    lines: list[str] = []
    for mission_name, terms in MISSION_KEYWORDS.items():
        if mission != "All Missions" and mission_name != mission:
            continue
        if terms:
            lines.append(f"- {mission_name}: {', '.join(terms)}")

    if mission == "All Missions" and CROSS_CUTTING_KEYWORDS:
        lines.append(f"- Cross-cutting: {', '.join(CROSS_CUTTING_KEYWORDS)}")

    if not lines:
        return "Error: Could not load keywords.py variables."

    return "\n".join(lines)


class ChatRequest(BaseModel):
    message: str
    signal_count: int = 5
    mission: str = "All Missions"
    time_filter: str = "Past Month"
    source_types: list[str] = []
    scan_mode: str = "general"


def _fallback_create(*_: Any, **__: Any) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[]))])


client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_fallback_create)))


def get_sheet_records(include_rejected: bool = True) -> list[dict[str, Any]]:
    _ = include_rejected
    return []


def upsert_signal(payload: dict[str, Any]) -> None:
    _ = payload


async def chat_endpoint(request: ChatRequest, stream: bool = False) -> dict[str, Any]:
    _ = stream
    bounded_count = 5 if request.signal_count <= 0 else min(50, request.signal_count)
    messages = [
        {"role": "system", "content": "Signal scout"},
        {"role": "user", "content": f"Generate exactly {bounded_count} seeds for: {request.message}"},
    ]

    collected: list[dict[str, Any]] = []
    while len(collected) < bounded_count:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4o-mini",
            messages=messages,
            tools=[],
        )
        tool_calls = response.choices[0].message.tool_calls or []
        if not tool_calls:
            break
        for tool_call in tool_calls:
            if tool_call.function.name != "display_signal_card":
                continue
            payload = json.loads(tool_call.function.arguments)
            published_date = payload.get("published_date", datetime.now().strftime("%Y-%m-%d"))
            if is_date_within_time_filter(published_date, request.time_filter, datetime.now()):
                upsert_signal(payload)
                collected.append(payload)
            if len(collected) >= bounded_count:
                break

    return {"ui_type": "signal_list", "items": collected[:bounded_count]}
