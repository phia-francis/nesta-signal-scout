from __future__ import annotations

import asyncio
import json
from functools import lru_cache
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel

from app.main import app
from keywords import CROSS_CUTTING_KEYWORDS, MISSION_KEYWORDS
from utils import is_date_within_time_filter, parse_source_date


class ChatRequest(BaseModel):
    message: str
    signal_count: int = 5
    mission: str = "All Missions"
    time_filter: str = "Past Year"
    source_types: list[str] = []
    scan_mode: str = "general"


class _DummyCompletions:
    def create(self, model: str, messages: list[dict[str, str]], tools: list[dict[str, Any]]) -> Any:
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[]))])


class _DummyChat:
    def __init__(self) -> None:
        self.completions = _DummyCompletions()


class _DummyClient:
    def __init__(self) -> None:
        self.chat = _DummyChat()


client = _DummyClient()


def get_sheet_records(include_rejected: bool = True) -> list[dict[str, Any]]:
    return []


def upsert_signal(payload: dict[str, Any]) -> None:
    return None


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


async def chat_endpoint(request: ChatRequest, stream: bool = False) -> dict[str, Any]:
    desired_count = max(5, min(50, int(request.signal_count or 5)))
    prompt = (
        "You are scanning for frontier signals. "
        f"User query: {request.message}. "
        f"Generate exactly {desired_count} seeds."
    )

    collected: list[dict[str, Any]] = []
    seen_urls: set[str] = set(record.get("url", "") for record in get_sheet_records(include_rejected=True))
    attempts = 0

    while len(collected) < desired_count and attempts < 10:
        attempts += 1
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You identify weak signals."},
                {"role": "user", "content": prompt},
            ],
            tools=[],
        )
        tool_calls = getattr(response.choices[0].message, "tool_calls", []) or []
        if not tool_calls:
            break

        for tool_call in tool_calls:
            if getattr(tool_call.function, "name", "") != "display_signal_card":
                continue
            try:
                payload = json.loads(tool_call.function.arguments)
            except (TypeError, json.JSONDecodeError):
                continue

            url = payload.get("url", "")
            if not url or url in seen_urls:
                continue

            item = {
                "title": payload.get("title", "Untitled Signal"),
                "url": url,
                "summary": payload.get("hook", ""),
                "mission": payload.get("mission", request.mission),
                "typology": payload.get("lenses", "Nascent"),
                "score": payload.get("score", 0),
                "published_date": payload.get("published_date", ""),
            }
            if not is_date_within_time_filter(item["published_date"], request.time_filter):
                continue

            seen_urls.add(url)
            collected.append(item)
            await asyncio.to_thread(upsert_signal, item)
            if len(collected) >= desired_count:
                break

    return {"ui_type": "signal_list", "items": collected}


__all__ = [
    "app",
    "parse_source_date",
    "is_date_within_time_filter",
    "build_allowed_keywords_menu",
    "ChatRequest",
    "chat_endpoint",
    "client",
    "get_sheet_records",
    "upsert_signal",
    "MISSION_KEYWORDS",
    "CROSS_CUTTING_KEYWORDS",
    "asyncio",
]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
