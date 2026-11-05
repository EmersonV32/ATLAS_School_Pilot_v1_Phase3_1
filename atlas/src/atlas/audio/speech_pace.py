"""Shared synthesis pace; independent of vocabulary, age and output language."""

from __future__ import annotations

import math
from dataclasses import dataclass

DEFAULT_SPEECH_SPEED = 0.90
SLOWER_SPEECH_SPEED = 0.80


def validate_speed(value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or not 0.6 <= value <= 1.5:
        raise ValueError("speech speed must be finite and between 0.6 and 1.5")
    return value


@dataclass
class SpeechPace:
    normal: float = DEFAULT_SPEECH_SPEED
    slow: float = SLOWER_SPEECH_SPEED
    enabled: bool = False

    def __post_init__(self) -> None:
        self.normal = validate_speed(self.normal)
        self.slow = validate_speed(self.slow)
        if self.slow > self.normal:
            raise ValueError("slower speech speed cannot exceed normal speed")

    @property
    def speed(self) -> float:
        return self.slow if self.enabled else self.normal


def apply_speech_pace(tts, accessibility) -> None:
    """Keep legacy/mock adapters compatible; only the explicit choice slows TTS."""
    setter = getattr(tts, "set_slower_pace", None)
    if callable(setter):
        setter("slower_pace" in accessibility)
