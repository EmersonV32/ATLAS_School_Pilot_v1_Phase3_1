"""Abstract TTS interface."""
from __future__ import annotations
from abc import ABC, abstractmethod


class BaseTTS(ABC):
    @abstractmethod
    def speak(self, text: str, language: str = "en") -> None:
        """Synthesise text and play it through the audio output."""
        ...
