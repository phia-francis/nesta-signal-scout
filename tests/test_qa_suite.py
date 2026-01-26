from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import main


@dataclass
class FakeRun:
    thread_id: str
    id: str


class FakeRuns:
    def __init__(self, statuses):
        self._statuses = iter(statuses)

    def retrieve(self, thread_id, run_id):
        return next(self._statuses)

    def submit_tool_outputs(self, thread_id, run_id, tool_outputs):
        return None

    def cancel(self, thread_id, run_id):
        return None


class FakeMessages:
    def list(self, thread_id):
        content = SimpleNamespace(text=SimpleNamespace(value="ok"))
        return SimpleNamespace(data=[SimpleNamespace(content=[content])])


class FakeThreads:
    def __init__(self, statuses, prompt_capture):
        self.runs = FakeRuns(statuses)
        self.messages = FakeMessages()
        self._prompt_capture = prompt_capture

    def create_and_run(self, assistant_id, thread):
        self._prompt_capture["prompt"] = thread["messages"][0]["content"]
        return FakeRun(thread_id="thread-1", id="run-1")


class FakeClient:
    def __init__(self, statuses, prompt_capture):
        self.beta = SimpleNamespace(threads=FakeThreads(statuses, prompt_capture))


def make_tool_call(tool_id, name, arguments):
    function = SimpleNamespace(name=name, arguments=json.dumps(arguments))
    return SimpleNamespace(id=tool_id, function=function)


def make_requires_action(tool_calls):
    submit = SimpleNamespace(tool_calls=tool_calls)
    return SimpleNamespace(status="requires_action", required_action=SimpleNamespace(submit_tool_outputs=submit))


def make_completed():
    return SimpleNamespace(status="completed")


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

    prompt_capture = {}
    statuses = [
        make_requires_action(tool_calls_batch_1),
        make_requires_action(tool_calls_batch_2),
        make_completed(),
    ]
    fake_client = FakeClient(statuses, prompt_capture)

    async def immediate(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(main, "client", fake_client)
    monkeypatch.setattr(main.asyncio, "to_thread", immediate)
    monkeypatch.setattr(main.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(main, "is_date_within_time_filter", lambda *_: True)

    request = main.ChatRequest(message="Find signals", signal_count=5, mission="All Missions")
    result = asyncio.run(main.chat_endpoint(request))

    assert result["ui_type"] == "signal_list"
    assert len(result["items"]) == 5
    urls = {item["url"] for item in result["items"]}
    assert len(urls) == 5


def test_chat_endpoint_signal_count_defaults_and_boundaries(monkeypatch):
    prompt_capture = {}
    statuses = [make_completed()]
    fake_client = FakeClient(statuses, prompt_capture)

    async def immediate(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(main, "client", fake_client)
    monkeypatch.setattr(main.asyncio, "to_thread", immediate)
    monkeypatch.setattr(main.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(main, "is_date_within_time_filter", lambda *_: True)

    request = main.ChatRequest(message="Topic", signal_count=0, mission="Invalid Mission")
    asyncio.run(main.chat_endpoint(request))
    assert "exactly 5 seeds" in prompt_capture["prompt"]

    prompt_capture.clear()
    statuses = [make_completed()]
    fake_client = FakeClient(statuses, prompt_capture)
    monkeypatch.setattr(main, "client", fake_client)

    request = main.ChatRequest(message="Topic", signal_count=50, mission="Invalid Mission")
    asyncio.run(main.chat_endpoint(request))
    assert "exactly 50 seeds" in prompt_capture["prompt"]


def test_is_date_within_time_filter_edge_cases():
    request_date = datetime(2024, 3, 1)
    assert main.is_date_within_time_filter("2024-02-29", "Past Month", request_date) is True
    assert main.is_date_within_time_filter("2023-03-01", "Past Year", request_date) is True
    assert main.is_date_within_time_filter("2023-02-28", "Past Year", request_date) is False
