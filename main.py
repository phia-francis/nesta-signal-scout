from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta
from functools import lru_cache
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel

from app.main import app
from keywords import CROSS_CUTTING_KEYWORDS, MISSION_KEYWORDS


def read_root() -> dict[str, str]:
    return {"status": "System Operational", "message": "Signal Scout Backend is Running"}


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
    return []


def upsert_signal(payload: dict[str, Any]) -> None:
    _ = payload


def parse_source_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    if text.lower() in {"recent", "unknown", "n/a", "na", "tbd", "yesterday"}:
        return None

    patterns = [
        "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y",
        "%d %B %Y", "%d %b %Y", "%B %Y", "%b %Y", "%Y",
    ]

    text = re.sub(r"[^A-Za-z0-9,\-/ ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    for pattern in patterns:
        try:
            parsed = datetime.strptime(text, pattern)
            if pattern in {"%B %Y", "%b %Y"}:
                return datetime(parsed.year, parsed.month, 1)
            if pattern == "%Y":
                return datetime(parsed.year, 1, 1)
            return parsed
        except ValueError:
            continue

    date_match = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", text)
    if date_match:
        return parse_source_date(date_match.group(1))
    return None


def is_date_within_time_filter(raw_date: str, time_filter: str, request_date: datetime | None = None) -> bool:
    parsed = parse_source_date(raw_date)
    if not parsed:
        return False
    now = request_date or datetime.now()
    if time_filter == "Past Month":
        return parsed >= now - timedelta(days=29)
    if time_filter == "Past Year":
        return parsed >= now - timedelta(days=366)
    return True


async def chat_endpoint(request: ChatRequest, stream: bool = False) -> dict[str, Any]:
    _ = stream
    bounded_count = 5 if request.signal_count <= 0 else min(50, request.signal_count)
    messages = [
        {"role": "system", "content": "Signal scout"},
        {"role": "user", "content": f"Generate exactly {bounded_count} seeds for: {request.message}"},
    ]

    collected: list[dict[str, Any]] = []
    while len(collected) < bounded_count:
        response = await asyncio.to_thread(client.chat.completions.create, model="gpt-4o-mini", messages=messages, tools=[])
        tool_calls = (response.choices[0].message.tool_calls or [])
        if not tool_calls:
            break
        for tool_call in tool_calls:
            if tool_call.function.name != "display_signal_card":
                continue
            payload = json.loads(tool_call.function.arguments)
            if is_date_within_time_filter(payload.get("published_date", datetime.now().strftime("%Y-%m-%d")), request.time_filter):
                upsert_signal(payload)
                collected.append(payload)
            if len(collected) >= bounded_count:
                break
    return {"ui_type": "signal_list", "items": collected[:bounded_count]}


__all__ = [
    "app",
    "build_allowed_keywords_menu",
    "read_root",
    "ChatRequest",
    "chat_endpoint",
    "client",
    "parse_source_date",
    "is_date_within_time_filter",
    "get_sheet_records",
    "upsert_signal",
]
