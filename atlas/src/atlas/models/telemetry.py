"""Telemetry model for privacy-safe structured logging.

Note what is deliberately absent: no raw audio, no raw images, no student
names, no API keys. Transcript is optional and off by default.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TelemetryEvent(BaseModel):
    """One structured log record, emitted as a single JSON line."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    session_id: str
    timestamp: str  # ISO 8601
    state: str
    event: str = ""
    language: str | None = None
    artwork_id: str | None = None
    vision_confidence: float | None = None
    retrieval_latency_ms: float | None = None
    llm_latency_ms: float | None = None
    tts_latency_ms: float | None = None
    state_latency_ms: float | None = None
    fallback_used: bool | None = None
    error_type: str | None = None
    # Only populated when settings.logging.log_transcripts is True, and even
    # then it is sanitized upstream. Default: None.
    transcript: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)
