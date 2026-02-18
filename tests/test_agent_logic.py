from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("Google Search_API_KEY", "test-google-key")
os.environ.setdefault("Google Search_CX", "test-google-cx")




from types import SimpleNamespace

from fastapi.testclient import TestClient

import keywords
from app.api.dependencies import get_scan_orchestrator, get_sheet_service
from app.domain.models import SignalCard
from app.main import app


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


def test_radar_route_streams_signalcard_payload_with_orchestrator_override():
    class FakeOrchestrator:
        async def fetch_signals(self, topic, *, mission, mode, friction_mode=False):
            return [
                SimpleNamespace(
                    title="Demo Signal",
                    url="https://example.com/demo",
                    summary="A short hook for testing.",
                    source="OpenAlex",
                    mission=mission,
                    date="2025-01-01",
                    score_activity=3.0,
                    score_attention=8.0,
                    score_recency=7.5,
                    final_score=6.25,
                    typology="Hype",
                    is_novel=False,
                    related_keywords=["ai startups trends"],
                    model_dump=lambda: {
                        "title": "Demo Signal",
                        "url": "https://example.com/demo",
                        "summary": "A short hook for testing.",
                        "source": "OpenAlex",
                        "mission": mission,
                        "date": "2025-01-01",
                        "score_activity": 3.0,
                        "score_attention": 8.0,
                        "score_recency": 7.5,
                        "final_score": 6.25,
                        "typology": "Hype",
                        "is_novel": False,
                        "related_keywords": ["ai startups trends"],
                    },
                )
            ], ["ai startups trends"]

        def process_signals(self, raw_signals, *, mission, related_terms):
            card = SignalCard(
                title="Demo Signal",
                url="https://example.com/demo",
                summary="A short hook for testing.",
                source="OpenAlex",
                mission=mission,
                date="2025-01-01",
                score_activity=3.0,
                score_attention=8.0,
                score_recency=7.5,
                final_score=6.25,
                typology="Hype",
                is_novel=False,
                related_keywords=related_terms,
            )
            yield card


    class FakeSheetService:
        async def get_existing_urls(self):
            return set()

        async def queue_signals_for_sync(self, signals):
            return None

    app.dependency_overrides[get_scan_orchestrator] = lambda: FakeOrchestrator()
    app.dependency_overrides[get_sheet_service] = lambda: FakeSheetService()
    client = TestClient(app)

    response = client.post(
        "/api/mode/radar",
        json={"mission": "A Healthy Life", "query": "AI"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Demo Signal" in response.text
    assert "related_keywords" in response.text
