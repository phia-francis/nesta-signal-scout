from __future__ import annotations

from datetime import datetime
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.api.routes import radar as main


def make_tool_call(tool_id, name, arguments):
    function = SimpleNamespace(name=name, arguments=json.dumps(arguments))
    return SimpleNamespace(id=tool_id, type="function", function=function)


def make_response(tool_calls):
    message = SimpleNamespace(content="", tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FakeCompletions:
    def __init__(self, responses):
        self._responses = responses

    async def create(self, model, messages, tools):
        return self._responses.pop(0)


class _FakeLLMService:
    def __init__(self, responses):
        self.client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions(responses)))


class _FakeSheetService:
    def __init__(self):
        self.saved = []

    async def get_all(self):
        return []

    async def save_signals_batch(self, signals):
        self.saved.extend(signals)


def test_chat_endpoint_accumulates_signals_batches(monkeypatch):
    today = datetime.now().strftime("%Y-%m-%d")
    tool_calls_batch_1 = [
        make_tool_call(
            f"tool-{idx}",
            "display_signal_card",
            {
                "title": f"Signal {idx}",
                "url": f"https://example.com/article-{idx}",
                "hook": "Hook",
                "score": 7,
                "published_date": today,
            },
        )
        for idx in range(1, 4)
    ]
    tool_calls_batch_2 = [
        make_tool_call(
            f"tool-{idx}",
            "display_signal_card",
            {
                "title": f"Signal {idx}",
                "url": f"https://example.com/article-{idx}",
                "hook": "Hook",
                "score": 7,
                "published_date": today,
            },
        )
        for idx in range(4, 6)
    ]

    responses = [
        make_response(tool_calls_batch_1),
        make_response(tool_calls_batch_2),
    ]
    llm_service = _FakeLLMService(responses)
    sheet_service = _FakeSheetService()

    monkeypatch.setattr(main, "is_date_within_time_filter", lambda *_: True)

    request = main.ChatRequest(message="Find signals", signal_count=5, mission="All Missions")
    result = asyncio.run(main.chat_endpoint(request, stream=False, llm_service=llm_service, sheet_service=sheet_service))

    assert result["ui_type"] == "signal_list"
    assert len(result["items"]) == 5
    urls = {item["url"] for item in result["items"]}
    assert len(urls) == 5


def test_chat_endpoint_signal_count_defaults_and_boundaries(monkeypatch):
    prompt_capture = {}

    class _CaptureCompletions:
        async def create(self, model, messages, tools):
            prompt_capture["prompt"] = messages[0]["content"]
            return make_response([])

    llm_service = SimpleNamespace(client=SimpleNamespace(chat=SimpleNamespace(completions=_CaptureCompletions())))
    sheet_service = _FakeSheetService()

    monkeypatch.setattr(main, "is_date_within_time_filter", lambda *_: True)

    request = main.ChatRequest(message="Topic", signal_count=0, mission="Invalid Mission")
    asyncio.run(main.chat_endpoint(request, stream=False, llm_service=llm_service, sheet_service=sheet_service))
    assert "exactly 5 seeds" in prompt_capture["prompt"]

    request = main.ChatRequest(message="Topic", signal_count=50, mission="Invalid Mission")
    asyncio.run(main.chat_endpoint(request, stream=False, llm_service=llm_service, sheet_service=sheet_service))
    assert "exactly 50 seeds" in prompt_capture["prompt"]


def test_is_date_within_time_filter_edge_cases():
    request_date = datetime(2024, 3, 1)
    assert main.is_date_within_time_filter("2024-02-29", "Past Month", request_date) is True
    assert main.is_date_within_time_filter("2023-03-01", "Past Year", request_date) is True
    assert main.is_date_within_time_filter("2023-02-28", "Past Year", request_date) is False
