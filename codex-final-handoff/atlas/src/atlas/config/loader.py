"""Load and merge configuration from YAML files and environment variables.

Precedence (lowest to highest):
    1. Settings model defaults
    2. config/settings.yaml
    3. config/dashboard_overrides.yaml (admin dashboard settings)
    4. Environment variables (ATLAS_* overrides + ATLAS_MODE)

Secrets are not loaded here. API keys are read at call time from the env
var named by `settings.llm.api_key_env`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from atlas.config.settings import Settings
from atlas.models.enums import EducationalLevel, Language, RunMode


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"expected a mapping in {path}, got {type(data).__name__}")
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge nested mappings while replacing scalar and list values."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_env_overrides(raw: dict[str, Any]) -> dict[str, Any]:
    """Apply a few well-known environment overrides.

    Kept intentionally small and explicit rather than a generic deep-merge,
    so the override surface is auditable.
    """
    mode = os.getenv("ATLAS_MODE")
    if mode:
        raw["mode"] = mode

    pack = os.getenv("ATLAS_DEFAULT_PACK")
    if pack:
        raw["default_pack_id"] = pack

    log_transcripts = os.getenv("ATLAS_LOG_TRANSCRIPTS")
    if log_transcripts is not None:
        raw.setdefault("logging", {})["log_transcripts"] = log_transcripts.lower() in (
            "1",
            "true",
            "yes",
        )

    logging_overrides = {
        "ATLAS_LOG_LIVE_STT": "log_live_stt",
        "ATLAS_LOG_LLM_RESPONSES": "log_llm_responses",
    }
    for env_name, field_name in logging_overrides.items():
        value = os.getenv(env_name)
        if value is not None:
            raw.setdefault("logging", {})[field_name] = value.lower() in (
                "1",
                "true",
                "yes",
            )

    llm_provider = os.getenv("ATLAS_LLM_PROVIDER")
    if llm_provider:
        raw.setdefault("llm", {})["provider"] = llm_provider

    cloud_llm = os.getenv("ATLAS_CLOUD_LLM_ENABLED")
    if cloud_llm is not None:
        raw.setdefault("llm", {})["cloud_llm_enabled"] = cloud_llm.lower() in (
            "1",
            "true",
            "yes",
        )

    speech_provider_overrides = {
        "ATLAS_STT_PROVIDER": "stt_provider",
        "ATLAS_TTS_PROVIDER": "tts_provider",
    }
    for env_name, field_name in speech_provider_overrides.items():
        value = os.getenv(env_name)
        if value:
            raw.setdefault("speech", {})[field_name] = value

    cloud_speech = os.getenv("ATLAS_CLOUD_SPEECH_ENABLED")
    if cloud_speech is not None:
        raw.setdefault("speech", {})["cloud_speech_enabled"] = (
            cloud_speech.lower() in ("1", "true", "yes")
        )

    cartesia_voice = os.getenv("ATLAS_CARTESIA_VOICE_ID")
    if cartesia_voice:
        raw.setdefault("speech", {})["cartesia_voice_id"] = cartesia_voice

    hardware_overrides = {
        "ATLAS_CAMERA_SOURCE": "camera_source",
        "ATLAS_HEADSET_NAME": "headset_name",
        "ATLAS_EV3_ADDRESS": "ev3_bt_address",
        "ATLAS_YOLO_BACKEND": "yolo_backend",
    }
    for env_name, field_name in hardware_overrides.items():
        value = os.getenv(env_name)
        if value:
            raw.setdefault("hardware", {})[field_name] = value

    enable_ev3 = os.getenv("ATLAS_ENABLE_EV3")
    if enable_ev3 is not None:
        raw.setdefault("hardware", {})["enable_ev3"] = enable_ev3.lower() in (
            "1",
            "true",
            "yes",
        )

    return raw


def load_settings(config_dir: str | Path = "config") -> Settings:
    """Build a validated Settings object."""
    config_dir = Path(config_dir)
    load_dotenv(config_dir.parent / ".env", override=False)
    raw = _read_yaml(config_dir / "settings.yaml")
    configured_path = raw.get("dashboard", {}).get("config_override_path")
    override_path = (
        Path(configured_path)
        if configured_path
        else config_dir / "dashboard_overrides.yaml"
    )
    if not override_path.is_absolute():
        override_path = config_dir.parent / override_path
    raw = _deep_merge(raw, _read_yaml(override_path))
    raw.setdefault("dashboard", {})["config_override_path"] = str(override_path)
    raw = _apply_env_overrides(raw)
    return Settings.model_validate(raw)


def load_profiles(config_dir: str | Path = "config") -> dict[str, dict[str, Any]]:
    """Load profile presets from profiles.yaml.

    Returned as plain dicts keyed by profile name; consumers map these onto
    SessionProfile. Validates that referenced enums exist.
    """
    config_dir = Path(config_dir)
    raw = _read_yaml(config_dir / "profiles.yaml")
    profiles = raw.get("profiles", {})
    for _name, spec in profiles.items():
        level = spec.get("educational_level")
        if level is not None:
            EducationalLevel(level)  # raises on invalid
        lang = spec.get("language")
        if lang is not None:
            Language(lang)  # raises on invalid
    return profiles


def load_hardware(config_dir: str | Path = "config") -> dict[str, Any]:
    """Load hardware.yaml as a plain dict (consumed by the device layer)."""
    return _read_yaml(Path(config_dir) / "hardware.yaml")


def get_run_mode(settings: Settings) -> RunMode:
    return settings.mode
