"""Pydantic request/response schemas for the teacher dashboard API.

Everything returned here must be privacy-safe: no raw audio/images, no
student names, no API keys, no prompts. Questions/answers appear only in
the live response to the teacher who asked, and in logs only under the
transcript-logging rules.
"""
from __future__ import annotations

from typing import Literal

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


class LLMConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["mock", "gemini", "openai", "kimi"] | None = None
    model: str | None = Field(default=None, min_length=1, max_length=100)
    cloud_llm_enabled: bool | None = None
    streaming_enabled: bool | None = None
    sentence_tts_enabled: bool | None = None
    timeout_s: float | None = Field(default=None, ge=1.0, le=60.0)


class SpeechConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stt_provider: Literal["whisper", "deepgram"] | None = None
    tts_provider: Literal["piper", "cartesia"] | None = None
    cloud_speech_enabled: bool | None = None
    offline_fallback_enabled: bool | None = None
    deepgram_model: str | None = Field(default=None, min_length=1, max_length=80)
    deepgram_language: str | None = Field(default=None, min_length=2, max_length=20)
    listen_duration_s: float | None = Field(default=None, ge=3.0, le=20.0)
    silero_threshold: float | None = Field(default=None, ge=0.05, le=0.95)
    silero_min_silence_ms: int | None = Field(default=None, ge=100, le=3000)
    cartesia_model: str | None = Field(default=None, min_length=1, max_length=80)
    cartesia_voice_id: str | None = Field(default=None, min_length=1, max_length=100)


class VisionConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    yolo_backend: Literal["auto", "pytorch", "tensorrt"] | None = None
    vision_conf_threshold: float | None = Field(default=None, ge=0.05, le=0.95)
    vision_mask_conf_threshold: float | None = Field(
        default=None, ge=0.05, le=0.95
    )
    vision_center_weight: float | None = Field(default=None, ge=0.0, le=1.0)
    vision_center_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    vision_hold_seconds: float | None = Field(default=None, ge=0.25, le=10.0)
    vision_gap_tolerance_s: float | None = Field(default=None, ge=0.0, le=3.0)
    manual_capture_crop_ratio: float | None = Field(
        default=None, ge=0.25, le=1.0
    )
    camera_width: int | None = Field(default=None, ge=160, le=3840)
    camera_height: int | None = Field(default=None, ge=120, le=2160)
    camera_fps: int | None = Field(default=None, ge=1, le=60)
    camera_reconnect_s: float | None = Field(default=None, ge=0.1, le=30.0)


class RagConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_k: int | None = Field(default=None, ge=1, le=20)
    dense_top_k: int | None = Field(default=None, ge=1, le=50)
    keyword_top_k: int | None = Field(default=None, ge=1, le=50)
    chunk_max_words: int | None = Field(default=None, ge=20, le=200)
    language_fallback_enabled: bool | None = None
    fallback_language: Literal["en", "fr", "es", "it"] | None = None


class LoggingConfigUpdate(BaseModel):
    """Testing telemetry controls; secrets and raw media are never accepted."""

    model_config = ConfigDict(extra="forbid")

    log_transcripts: bool | None = None
    log_live_stt: bool | None = None
    log_llm_responses: bool | None = None


class DashboardConfigUpdate(BaseModel):
    """Admin-editable, non-secret settings persisted for the next restart."""

    model_config = ConfigDict(extra="forbid")

    llm: LLMConfigUpdate | None = None
    speech: SpeechConfigUpdate | None = None
    hardware: VisionConfigUpdate | None = None
    rag: RagConfigUpdate | None = None
    logging: LoggingConfigUpdate | None = None
