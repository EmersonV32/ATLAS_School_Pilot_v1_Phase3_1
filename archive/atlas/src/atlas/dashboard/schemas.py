"""Pydantic request/response schemas for the teacher dashboard API.

Everything returned here must be privacy-safe: no raw audio/images, no
student names, no API keys, no prompts. Questions/answers appear only in
the live response to the teacher who asked, and in logs only under the
transcript-logging rules.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SessionProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str | None = None          # en | fr | es | it
    profile: str | None = None           # EducationalLevel value
    pack_id: str | None = None
    accessibility_mode: bool | None = None


class ManualArtworkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artwork_id: str


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)
    language: str | None = None
    profile: str | None = None


class AskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    language: str
    grounded: bool
    fallback_used: bool
    filtered: bool
    confidence: str
    used_chunk_ids: list[str] = Field(default_factory=list)
    artwork_id: str | None = None
    retrieval_latency_ms: float | None = None
    total_latency_ms: float | None = None
    error: str | None = None


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    reset: bool = True


class DemoSimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # artwork:<artwork_id> | low_confidence | llm_timeout | tts_failure | reset
    scenario: str
