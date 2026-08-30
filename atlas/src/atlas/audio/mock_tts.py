"""Mock TTS — prints synthesised text to console instead of playing audio."""
from __future__ import annotations

import logging

from .tts import BaseTTS

logger = logging.getLogger(__name__)


class MockTTS(BaseTTS):
    def __init__(self) -> None:
        self.output_device_name = "Mock output"
        self.volume_percent = 100

    def set_output_device(self, output_device_name: str) -> None:
        self.output_device_name = output_device_name

    def set_volume(self, volume_percent: int) -> None:
        self.volume_percent = min(100, max(0, int(volume_percent)))

    def audio_settings(self) -> dict[str, object]:
        return {
            "output_device_name": self.output_device_name,
            "volume_percent": self.volume_percent,
        }

    def cue(self) -> bool:
        print("[TTS:CUE]")
        return True

    def speak(self, text: str, language: str = "en") -> bool:
        logger.info("[TTS:%s] %s", language.upper(), text)
        print(f"[TTS:{language.upper()}] {text}")
        return True
