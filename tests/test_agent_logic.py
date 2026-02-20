from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("Google Search_API_KEY", "test-google-key")
os.environ.setdefault("Google Search_CX", "test-google-cx")


from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.dependencies import get_scan_orchestrator, get_sheet_service
from app.domain.models import SignalCard
from app.main import app


def test_radar_route_returns_signalcard_payload_with_orchestrator_override():
    class FakeOrchestrator:
        async def execute_scan(self, query, mission, mode):
            return {
                "signals": [
                    SignalCard(
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
                    )
                ],
                "related_terms": ["ai startups trends"],
                "warnings": None,
                "mode": mode,
            }

    class FakeSheetService:
        async def get_existing_urls(self):
            return set()

        async def queue_signals_for_sync(self, signals):
            return None

    app.dependency_overrides[get_scan_orchestrator] = lambda: FakeOrchestrator()
    app.dependency_overrides[get_sheet_service] = lambda: FakeSheetService()
    client = TestClient(app)

    response = client.post(
        "/scan/radar",
        json={"mission": "A Healthy Life", "query": "AI"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "signals" in data
    assert len(data["signals"]) > 0
    assert data["signals"][0]["title"] == "Demo Signal"
    assert "related_keywords" in data["signals"][0]
