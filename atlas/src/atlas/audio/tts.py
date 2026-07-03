"""Abstract TTS interface."""
from __future__ import annotations
from abc import ABC, abstractmethod


class BaseTTS(ABC):
    @abstractmethod
    def speak(self, text: str, language: str = "en") -> bool:
        """Synthesise text and play it through the audio output.

        Returns True if audio was produced, False on failure. Callers must
        treat False as "fall back to showing the answer as text" — never
        crash the cycle because TTS failed.
        """
        ...
