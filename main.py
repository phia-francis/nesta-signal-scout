from __future__ import annotations

import asyncio
from functools import lru_cache

from app.main import app
from app.legacy_compat import ChatRequest, chat_endpoint, client, get_sheet_records, upsert_signal
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
