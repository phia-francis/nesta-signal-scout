from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SignalCard(BaseModel):
    title: str
    url: str
    summary: str
    typology: str = Field(..., description="Hidden Gem, Hype, Established, or Nascent")
    score_activity: float = 0.0
    score_attention: float = 0.0
    mission: str
    sparkline: List[int] = Field(default_factory=list)


class RadarRequest(BaseModel):
    mission: str
    topic: Optional[str] = None
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
