"""Load and merge configuration from YAML files and environment variables.

Precedence (lowest to highest):
    1. Settings model defaults
    2. config/settings.yaml
    3. Environment variables (ATLAS_* overrides + ATLAS_MODE)

Secrets are not loaded here. API keys are read at call time from the env
var named by `settings.llm.api_key_env`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

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
        raw.setdefault("logging", {})["log_transcripts"] = (
            log_transcripts.lower() in ("1", "true", "yes")
        )

    llm_provider = os.getenv("ATLAS_LLM_PROVIDER")
    if llm_provider:
        raw.setdefault("llm", {})["provider"] = llm_provider

    return raw


def load_settings(config_dir: str | Path = "config") -> Settings:
    """Build a validated Settings object."""
    config_dir = Path(config_dir)
    raw = _read_yaml(config_dir / "settings.yaml")
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
    for name, spec in profiles.items():
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
