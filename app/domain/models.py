from __future__ import annotations

from datetime import datetime
from typing import Any, List

from pydantic import BaseModel, Field


class RawSignal(BaseModel):
    """Signal payload returned directly from upstream sources."""

    source: str
    title: str
    url: str
    abstract: str = ""
    date: datetime
    raw_score: float = 0.0
    mission: str = "General"
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_novel: bool = False
    origin_country: str = "Global"


class ScoredSignal(RawSignal):
    """Processed signal with calculated scoring dimensions."""

    score_activity: float
    score_attention: float
    score_recency: float
    final_score: float
    typology: str


class SignalCard(BaseModel):
    """The final output sent to the UI."""

    title: str
    url: str
    summary: str
    source: str
    mission: str
    date: str
    score_activity: float
    score_attention: float
    score_recency: float
    final_score: float
    typology: str
    is_novel: bool = False
    origin_country: str = "Global"
    sparkline: List[int] = Field(default_factory=list, description="Activity trend")
    related_keywords: list[str] = Field(default_factory=list)
    narrative_group: str | None = Field(default=None, description="Thematic cluster name")


class RadarRequest(BaseModel):
    mission: str
    topic: str | None = None
    mode: str = "radar"
    query: str | None = None
    friction_mode: bool = False


class ResearchRequest(BaseModel):
    query: str
    time_horizon: str = "y1"


class PolicyRequest(BaseModel):
    mission: str
    topic: str


class UpdateSignalRequest(BaseModel):
    url: str
    status: str


SignalPayload = dict[str, Any]
