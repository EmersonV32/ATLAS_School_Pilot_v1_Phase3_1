"""Mock TTS — prints synthesised text to console instead of playing audio."""
from __future__ import annotations
import logging
from .tts import BaseTTS

logger = logging.getLogger(__name__)


class MockTTS(BaseTTS):
    def speak(self, text: str, language: str = "en") -> None:
        logger.info("[TTS:%s] %s", language.upper(), text)
        print(f"[TTS:{language.upper()}] {text}")
