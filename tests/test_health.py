"""
Tests for the /api/health endpoint.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_awake():
    """Test that /api/health returns status 'awake' immediately."""
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "awake"
    assert "message" in data
