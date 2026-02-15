"""Typed API contracts for frontend/backend integration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = ""
    conversationId: str | None = None
    disease: str | None = None
    subtype: str | None = None


class Citation(BaseModel):
    title: str
    year: int | None = None
    pmid: str | None = None
    nct: str | None = None


class TrialSignal(BaseModel):
    terminationReason: str | None = None
    whyStopped: str | None = None


class KGSignal(BaseModel):
    score: float | None = None
    topTargets: list[str] = Field(default_factory=list)


class FAERSSignal(BaseModel):
    inverseSignal: bool | None = None
    ror: float | None = None
    ci95: list[float | None] = Field(default_factory=list)


class DockSignal(BaseModel):
    target: str | None = None
    confidence: float | None = None


class Signals(BaseModel):
    trials: TrialSignal = Field(default_factory=TrialSignal)
    kg: KGSignal = Field(default_factory=KGSignal)
    faers: FAERSSignal = Field(default_factory=FAERSSignal)
    dock: DockSignal = Field(default_factory=DockSignal)


class RankedCandidate(BaseModel):
    drug: str
    overallScore: float
    signals: Signals = Field(default_factory=Signals)
    safetyFlags: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class QueryArtifact(BaseModel):
    disease: str
    subtype: str | None = None


class Artifacts(BaseModel):
    query: QueryArtifact
    rankedCandidates: list[RankedCandidate] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    conversationId: str
    assistantMessage: str
    artifacts: Artifacts | None = None
