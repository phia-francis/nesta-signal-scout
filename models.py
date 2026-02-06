from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SignalCard(BaseModel):
    title: str
    summary: str
    url: str
    typology: str = Field(..., description="HOT, EMERGING, STABILISING, or DORMANT")
    novelty_score: float = 0.0
    growth_metric: float = 0.0
    magnitude_metric: float = 0.0
    sparkline: List[int] = Field(default_factory=list)
    mission: str


class RadarRequest(BaseModel):
    mission: str
    topic: Optional[str] = None
    friction_mode: bool = False


class ResearchRequest(BaseModel):
    query: str
    time_horizon: str = "y1"
    friction_mode: bool = False


class PolicyRequest(BaseModel):
    mission: str
    topic: str


class UpdateSignalRequest(BaseModel):
    url: str
    status: str


class FeedbackRequest(BaseModel):
    signal_id: str
    relevant: bool


class ChatRequest(BaseModel):
    message: str
    signal_count: int = 5
    time_filter: str = "Past Month"
    source_types: List[str] = Field(default_factory=list)
    scan_mode: str = "general"
    mission: str = "All Missions"
