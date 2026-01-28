import asyncio
import json
import os
from datetime import datetime
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import keywords
import main


def test_generate_broad_scan_queries_returns_single_query(monkeypatch):
    class FakeChatCompletions:
        def create(self, model, messages):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ai startups trends"))]
            )

    class FakeChat:
        def __init__(self):
            self.completions = FakeChatCompletions()

    class FakeOpenAI:
        def __init__(self, api_key=None):
            self.chat = FakeChat()

    monkeypatch.setattr(keywords, "OpenAI", FakeOpenAI)

    results = keywords.generate_broad_scan_queries(["AI"], num_signals=1)

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]


def test_chat_endpoint_handles_display_signal_card(monkeypatch):
    today = datetime.now().strftime("%Y-%m-%d")
    tool_args = {
        "title": "Demo Signal",
        "url": "https://example.com/demo",
        "hook": "A short hook for testing.",
        "score": 7,
        "mission": "A Healthy Life",
        "lenses": "Policy",
        "score_novelty": 7,
        "score_evidence": 7,
        "score_evocativeness": 6,
        "published_date": today,
    }
    tool_call = SimpleNamespace(
        id="call_1",
        type="function",
        function=SimpleNamespace(
            name="display_signal_card",
            arguments=json.dumps(tool_args),
        ),
    )
    fake_message = SimpleNamespace(content="", tool_calls=[tool_call])
    fake_response = SimpleNamespace(choices=[SimpleNamespace(message=fake_message)])

    def fake_create(model, messages, tools):
        return fake_response

    monkeypatch.setattr(main.client.chat.completions, "create", fake_create)
    monkeypatch.setattr(main, "get_sheet_records", lambda include_rejected=True: [])
    monkeypatch.setattr(main, "upsert_signal", lambda payload: None)

    req = main.ChatRequest(
        message="Scout for innovations",
        signal_count=1,
        time_filter="Past Month",
        source_types=[],
        scan_mode="general",
    )

    response = asyncio.run(main.chat_endpoint(req))

    assert response["ui_type"] == "signal_list"
    assert len(response["items"]) == 1
    assert response["items"][0]["title"] == "Demo Signal"
