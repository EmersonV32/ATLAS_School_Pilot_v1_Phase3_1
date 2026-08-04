"""Typed application settings.

Settings are assembled by `loader.py` from YAML files plus environment
variables. Secrets (API keys) are NEVER stored in YAML or in code; they are
read from the environment / .env at the point of use.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from atlas.models.enums import RunMode


class PathsSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_dir: Path = Path("data")
    content_packs_dir: Path = Path("data/content_packs")
    chroma_dir: Path = Path("data/chroma")
    sqlite_dir: Path = Path("data/sqlite")
    logs_dir: Path = Path("data/logs")


class RagSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_k: int = 5
    dense_top_k: int = 10
    keyword_top_k: int = 10
    rrf_k: int = 60  # Reciprocal Rank Fusion constant
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    use_dense: bool = True
    use_keyword: bool = True
    use_cross_encoder_reranker: bool = False  # extension point


class LLMSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "mock"  # "mock" | "gemini"
    model: str = "gemini-2.5-flash"  # Gemini model name when provider=gemini
    timeout_s: float = 8.0
    max_regenerations: int = 1
    # Explicit disclosure switch: cloud LLM calls happen only when True.
    cloud_llm_enabled: bool = False
    # The API key env var NAME (not the key itself).
    api_key_env: str = "GEMINI_API_KEY"


class LoggingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str = "INFO"
    json_lines: bool = True
    log_transcripts: bool = False  # privacy default: off
    retention_days: int = 30


class HardwareSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera_index: int = 0
    headset_name: str = "Shokz OpenComm2 UC"
    enable_servo: bool = False
    enable_ev3: bool = False
    # Device-mode asset paths / addresses. Empty string = not configured;
    # adapters must fail gracefully (never crash dev mode).
    yolo_model_path: str = "models/atlas_yolo.pt"
    whisper_model_size: str = "small"
    whisper_compute_type: str = "int8"  # good default for Jetson
    piper_binary_path: str = ""  # "" -> use piper from PATH
    piper_voice_en: str = "voices/en_US-amy-medium.onnx"
    piper_voice_fr: str = "voices/fr_FR-mls-medium.onnx"
    ev3_bt_address: str = ""  # e.g. "00:16:53:AA:BB:CC"; "" = EV3 disabled


class DashboardSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = "127.0.0.1"  # localhost only; never expose publicly
    port: int = 8765
    # Env var NAME holding the local admin token (not the token itself).
    admin_token_env: str = "ATLAS_ADMIN_TOKEN"


class PrivacySettings(BaseModel):
    """School-pilot privacy defaults. All storage of raw media is opt-in."""

    model_config = ConfigDict(extra="forbid")

    store_raw_audio: bool = False
    store_raw_images: bool = False
    store_face_data: bool = False
    student_names_required: bool = False
    anonymous_session_ids: bool = True
    session_memory_persistent: bool = False
    # When transcript logging is enabled, log the sanitized transcript only.
    transcript_logging_sanitized: bool = True


class Settings(BaseModel):
    """Root settings object passed around via the dependency container."""

    model_config = ConfigDict(extra="forbid")

    mode: RunMode = RunMode.DEV
    default_pack_id: str = "demo_pack"
    paths: PathsSettings = Field(default_factory=PathsSettings)
    rag: RagSettings = Field(default_factory=RagSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    hardware: HardwareSettings = Field(default_factory=HardwareSettings)
    dashboard: DashboardSettings = Field(default_factory=DashboardSettings)
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
