from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    time_filter: str = "Past Month"
    source_types: List[str] = Field(default_factory=list)
    tech_mode: bool = False
    mission: str = "All Missions"
    signal_count: Optional[int] = None
    scan_mode: str = "general"


class GenerateQueriesRequest(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    count: int = 5


class Signal(BaseModel):
    title: str
    hook: str
    analysis: str
    implication: str
    score_novelty: int
    score_evidence: int
    score_impact: int
    mission: str = Field(
        description=(
            "One of: '🌳 A Sustainable Future', '📚 A Fairer Start', "
            "'❤️‍🩹 A Healthy Life', or 'Mission Adjacent - [Topic]'"
        )
    )
    url: Optional[str] = None
    source_date: Optional[str] = None
    lenses: Optional[str] = None
    score_evocativeness: Optional[int] = None


class SynthesisRequest(BaseModel):
    signals: List[Dict[str, Any]]


class UpdateSignalRequest(BaseModel):
    url: str
    hook: Optional[str] = None
    analysis: Optional[str] = None
    implication: Optional[str] = None
    title: Optional[str] = None
    score: Optional[int] = None
    score_novelty: Optional[int] = None
    score_evidence: Optional[int] = None
    score_impact: Optional[int] = None
    score_evocativeness: Optional[int] = None
    mission: Optional[str] = None
    lenses: Optional[str] = None
    source_date: Optional[str] = None


class EnrichRequest(BaseModel):
    url: str
