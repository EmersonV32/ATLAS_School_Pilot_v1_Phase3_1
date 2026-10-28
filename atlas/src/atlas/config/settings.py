"""Typed application settings.

Settings are assembled by `loader.py` from YAML files plus environment
variables. Secrets (API keys) are NEVER stored in YAML or in code; they are
read from the environment / .env at the point of use.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    # Retrieve broadly enough that intent-aware reranking can see useful
    # chunks even after content packs grow beyond ten entries per artwork.
    dense_top_k: int = 20
    keyword_top_k: int = 10
    rrf_k: int = 60  # Reciprocal Rank Fusion constant
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_local_files_only: bool = True
    use_dense: bool = True
    use_keyword: bool = True
    use_cross_encoder_reranker: bool = False  # extension point
    chunk_max_words: int = Field(default=55, ge=20, le=200)
    language_fallback_enabled: bool = True
    fallback_language: Literal["en", "fr", "es", "it", "zh"] = "en"


class LLMSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["mock", "gemini", "openai", "kimi"] = "mock"
    model: str = "gemini-2.5-flash"
    timeout_s: float = 8.0
    max_regenerations: int = 1
    # Explicit disclosure switch: cloud LLM calls happen only when True.
    cloud_llm_enabled: bool = False
    # API key environment variable NAMES (never the keys themselves).
    gemini_api_key_env: str = "GEMINI_API_KEY"
    openai_api_key_env: str = "OPENAI_API_KEY"
    kimi_api_key_env: str = "MOONSHOT_API_KEY"
    # Kimi exposes an OpenAI-compatible Chat Completions endpoint.
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    streaming_enabled: bool = True
    # Segmenting one answer into multiple TTS requests can change timbre or
    # trigger a fallback voice between sentences. ATLAS speaks each complete
    # answer in one request instead.
    sentence_tts_enabled: bool = False


class LoggingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str = "INFO"
    json_lines: bool = True
    log_transcripts: bool = False  # privacy default: off
    log_live_stt: bool = False
    log_llm_responses: bool = False
    retention_days: int = 30


class HardwareSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # A numeric string opens a local camera ("0"). A URL opens the XIAO
    # ESP32-S3 Sense MJPEG stream ("http://192.168.x.x:81/stream").
    camera_source: str = "0"
    # ESP32 camera control endpoint. When set, ATLAS reapplies the expected
    # sensor profile whenever the MJPEG stream opens or reconnects.
    camera_control_url: str = ""
    camera_framesize: int = Field(default=11, ge=0, le=21)
    camera_jpeg_quality: int = Field(default=14, ge=4, le=63)
    camera_index: int = 0
    camera_width: int = 1280
    camera_height: int = 720
    camera_fps: int = 15
    camera_rotation_degrees: int = 0
    camera_reconnect_s: float = 1.0
    # Independent IMX477/UC-517 preview. It is opened lazily by the admin tab,
    # so a missing CSI camera never blocks ATLAS or either dashboard.
    arducam_enabled: bool = True
    arducam_sensor_id: int = Field(default=0, ge=0, le=7)
    arducam_width: int = Field(default=1920, ge=160, le=4056)
    arducam_height: int = Field(default=1080, ge=120, le=3040)
    arducam_fps: int = Field(default=30, ge=1, le=60)
    arducam_flip_method: int = Field(default=0, ge=0, le=7)
    arducam_reconnect_s: float = Field(default=1.0, ge=0.1, le=30.0)
    headset_name: str = "Shokz OpenComm2 UC"
    # Empty keeps speech output on the headset; set to a speaker for split routing.
    audio_output_name: str = ""
    judge_speaker_name: str = "UACDemoV1.0"
    audio_volume_percent: int = Field(default=100, ge=0, le=100)
    headset_button_enabled: bool = True
    # Empty means discover the Shokz Consumer Control evdev node by name.
    headset_button_device: str = ""
    headset_button_key_code: int = Field(default=164, ge=1, le=767)
    headset_button_click_window_s: float = Field(default=0.55, ge=0.2, le=1.5)
    # The Shokz play/pause key has one deliberate in-experience action.
    headset_button_action: Literal["manual_capture"] = "manual_capture"
    enable_servo: bool = False
    enable_ev3: bool = False
    # Device-mode asset paths / addresses. Empty string = not configured;
    # adapters must fail gracefully (never crash dev mode).
    yolo_model_path: str = "models/atlas_yolo.pt"
    yolo_tensorrt_path: str = "models/atlas_yolo.engine"
    yolo_backend: Literal["auto", "pytorch", "tensorrt"] = "auto"
    # Preserve Jetson GPU 0; "cpu" permits hardware-free real-model checks.
    yolo_device: str | int = 0
    yolo_imgsz: int = 416
    vision_rotation_degrees: Literal[0, 90, 180, 270] = 0
    vision_conf_threshold: float = 0.24
    vision_mask_conf_threshold: float = 0.45
    vision_center_weight: float = 0.55
    vision_center_threshold: float = 0.35
    vision_hold_seconds: float = 2.0
    vision_gap_tolerance_s: float = Field(default=0.8, ge=0.0, le=3.0)
    vision_clear_frames: int = 4
    vision_poll_interval_s: float = 0.05
    manual_capture_enabled: bool = True
    manual_capture_keyboard_enabled: bool = True
    manual_capture_crop_ratio: float = 0.70
    manual_capture_jpeg_quality: int = 85
    whisper_model_size: str = "small"
    # CTranslate2 CUDA wheels are inconsistent on JetPack. CPU int8 is the
    # reliable default; set whisper_device=cuda only after preflight proves it.
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_beam_size: int = 5
    whisper_local_files_only: bool = True
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    piper_binary_path: str = ""  # "" -> use piper from PATH
    piper_voice_en: str = "~/piper_voices/en_US-ryan-low.onnx"
    piper_voice_fr: str = "~/piper_voices/fr_FR-siwis-medium.onnx"
    piper_voice_es: str = ""
    piper_voice_it: str = ""
    piper_voice_zh: str = ""
    ev3_bt_address: str = ""  # e.g. "00:16:53:AA:BB:CC"; "" = EV3 disabled
    ev3_mailbox_name: str = "atlas"
    ev3_connect_timeout_s: float = 12.0
    ev3_status_led_enabled: bool = False


class CameraPanSettings(BaseModel):
    """Optional positional SG90; hardware setup is never changed by ATLAS."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    enabled: bool = False
    calibration_confirmed: bool = False
    driver: Literal["pca9685", "jetson_pwm"] = "pca9685"
    # BOARD numbers, not BCM: verified reComputer Super J401 routing only.
    jetson_board_pin: Literal[15, 32] = 32
    pinmux_confirmed: bool = False
    power_confirmed: bool = False
    startup_mode: Literal["sweep", "hold"] = "sweep"
    i2c_bus: int | None = Field(default=None, ge=0, le=255)
    i2c_address: int = Field(default=0x40, ge=0x40, le=0x6F)
    channel: int = Field(default=0, ge=0, le=15)
    oscillator_hz: int = Field(default=25_000_000, ge=20_000_000, le=30_000_000)
    min_angle: float = Field(default=0.0, ge=0, le=180)
    max_angle: float = Field(default=180.0, ge=0, le=180)
    center_angle: float = Field(default=90.0, ge=0, le=180)
    # Conservative placeholders, NOT proof of a physical 180-degree range.
    min_pulse_us: int = Field(default=1000, ge=500, le=2500)
    max_pulse_us: int = Field(default=2000, ge=500, le=2500)
    sweep_speed_deg_s: float = Field(default=5.0, ge=0.5, le=15)
    manual_speed_deg_s: float = Field(default=15.0, ge=0.5, le=30)

    @model_validator(mode="after")
    def validate_travel(self) -> CameraPanSettings:
        if not self.min_angle < self.max_angle:
            raise ValueError("camera pan requires min_angle < max_angle")
        if not self.min_angle <= self.center_angle <= self.max_angle:
            raise ValueError("camera pan center must be within the travel limits")
        if not self.min_pulse_us < self.max_pulse_us:
            raise ValueError("camera pan requires min_pulse_us < max_pulse_us")
        return self


class SpeechSettings(BaseModel):
    """Speech providers and privacy-conscious streaming controls."""

    model_config = ConfigDict(extra="forbid")

    stt_provider: Literal["whisper", "deepgram"] = "whisper"
    tts_provider: Literal["piper", "cartesia"] = "piper"
    # This explicit switch must be true before microphone audio or answer text
    # is sent to a cloud speech provider.
    cloud_speech_enabled: bool = False
    offline_fallback_enabled: bool = True

    deepgram_api_key_env: str = "DEEPGRAM_API_KEY"
    deepgram_model: str = "nova-3"
    deepgram_language: str = "multi"
    deepgram_endpointing_ms: int = 400
    deepgram_final_timeout_s: float = 3.0
    deepgram_keyterms: list[str] = Field(default_factory=list)
    listen_duration_s: float = 8.0
    # Waiting for first speech and recording an utterance are separate limits.
    max_utterance_s: float = Field(default=45.0, ge=5, le=120, allow_inf_nan=False)

    silero_threshold: float = 0.5
    silero_model_path: str = "models/silero_vad.onnx"
    silero_min_speech_ms: int = 250
    silero_min_silence_ms: int = 2000
    silero_hesitation_silence_ms: int = Field(default=4000, ge=200, le=10000)
    silero_scripted_faq_silence_ms: int = Field(default=600, ge=0, le=2000)
    silero_pre_roll_ms: int = 250

    cartesia_api_key_env: str = "CARTESIA_API_KEY"
    cartesia_model: str = "sonic-3.5"
    cartesia_api_version: str = "2026-03-01"
    # Jameson is a multilingual male Cartesia voice. This ID is deliberately
    # configuration, not code, so the future admin dashboard can replace it.
    cartesia_voice_id: str = "a5136bf9-224c-4d76-b823-52bd5efcffcc"
    cartesia_sample_rate: int = 24000
    cartesia_response_timeout_s: float = 15.0


class DashboardSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    host: str = "127.0.0.1"  # localhost only; never expose publicly
    port: int = 8765
    # May be disabled only for a loopback-bound prototype dashboard.
    admin_auth_required: bool = True
    # Allows non-destructive simulation controls while bound to loopback.
    allow_demo_controls: bool = False
    # Env var NAME holding the local admin token (not the token itself).
    admin_token_env: str = "ATLAS_ADMIN_TOKEN"
    # Safe dashboard edits are stored separately from the reviewed base config.
    config_override_path: Path = Path("config/dashboard_overrides.yaml")


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
    camera_pan: CameraPanSettings = Field(default_factory=CameraPanSettings)
    speech: SpeechSettings = Field(default_factory=SpeechSettings)
    dashboard: DashboardSettings = Field(default_factory=DashboardSettings)
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
