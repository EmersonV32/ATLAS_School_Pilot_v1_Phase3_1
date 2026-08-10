"""Small helpers for selecting the Shokz USB audio device by name."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any


def device_name_score(candidate: str, requested: str) -> int:
    candidate_l = candidate.lower()
    requested_l = requested.lower()
    tokens = [
        token for token in re.findall(r"[a-z0-9]+", requested_l) if len(token) > 2
    ]
    score = sum(2 for token in tokens if token in candidate_l)
    if requested_l in candidate_l:
        score += 10
    if any(alias in candidate_l for alias in ("shokz", "opencomm", "loop")):
        score += 3
    return score


def find_sounddevice_input(requested: str) -> int | None:
    import sounddevice as sd  # type: ignore

    devices = list(sd.query_devices())
    virtual_inputs: dict[str, int] = {}
    requested_index: int | None = None
    requested_score = 0
    for index, info in enumerate(devices):
        if int(info.get("max_input_channels", 0)) < 1:
            continue
        name = str(info.get("name", ""))
        if name.lower() in {"pulse", "default"}:
            virtual_inputs[name.lower()] = index
        score = device_name_score(name, requested)
        if score > requested_score:
            requested_index, requested_score = index, score

    pulse_defaults = find_pulse_defaults()
    pulse_is_requested = bool(
        device_name_score(pulse_defaults.get("source", ""), requested)
    )
    if (
        requested_index is not None
        and "pulse" in virtual_inputs
        and (pulse_is_requested or configure_pulse_capture(requested))
    ):
        return virtual_inputs["pulse"]
    if pulse_is_requested:
        for preferred_name in ("pulse", "default"):
            if preferred_name in virtual_inputs:
                return virtual_inputs[preferred_name]
    if requested_index is not None:
        return requested_index
    return None


def parse_pactl_defaults(output: str) -> dict[str, str]:
    defaults: dict[str, str] = {}
    for line in output.splitlines():
        label, separator, value = line.partition(":")
        if not separator:
            continue
        key = {
            "Default Sink": "sink",
            "Default Source": "source",
        }.get(label.strip())
        if key:
            defaults[key] = value.strip()
    return defaults


def find_pulse_defaults() -> dict[str, str]:
    try:
        result = subprocess.run(
            ["pactl", "info"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    return parse_pactl_defaults(result.stdout)


def select_pulse_device(
    output: str, requested: str, *, include_monitors: bool = True
) -> str | None:
    """Select the best named device from ``pactl list short`` output."""
    best: tuple[int, str] | None = None
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            fields = line.split()
        if len(fields) < 2:
            continue
        name = fields[1]
        if not include_monitors and name.endswith(".monitor"):
            continue
        score = device_name_score(name, requested)
        if score and (best is None or score > best[0]):
            best = (score, name)
    return best[1] if best else None


def _find_pulse_device(
    requested: str, kind: str, *, include_monitors: bool = True
) -> str | None:
    try:
        result = subprocess.run(
            ["pactl", "list", "short", kind],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return select_pulse_device(
        result.stdout, requested, include_monitors=include_monitors
    )


def find_pulse_playback(requested: str) -> str | None:
    return _find_pulse_device(requested, "sinks")


def find_pulse_capture(requested: str) -> str | None:
    return _find_pulse_device(requested, "sources", include_monitors=False)


def configure_pulse_capture(requested: str) -> str | None:
    """Pin PulseAudio capture to the requested headset for this process."""
    source = find_pulse_capture(requested)
    if source is None:
        return None
    os.environ["PULSE_SOURCE"] = source
    try:
        result = subprocess.run(
            ["pactl", "set-default-source", source],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return source
    return source


def find_alsa_playback(requested: str) -> str | None:
    """Return ``plughw:CARD,DEVICE`` for the best matching ALSA card."""
    try:
        output = subprocess.run(
            ["aplay", "-l"], capture_output=True, text=True, timeout=3, check=False
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    best: tuple[int, str] | None = None
    pattern = re.compile(
        r"card\s+(\d+):.*?\[(.*?)\],\s*device\s+(\d+):.*?\[(.*?)\]",
        re.IGNORECASE,
    )
    for match in pattern.finditer(output):
        card, card_name, device, device_name = match.groups()
        score = device_name_score(f"{card_name} {device_name}", requested)
        if score and (best is None or score > best[0]):
            best = (score, f"plughw:{card},{device}")
    return best[1] if best else None


def audio_device_snapshot() -> list[dict[str, Any]]:
    try:
        import sounddevice as sd  # type: ignore

        return [dict(item) for item in sd.query_devices()]
    except Exception:
        return []
