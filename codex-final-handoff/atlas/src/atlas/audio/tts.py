"""Abstract TTS interface."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseTTS(ABC):
    def warm_up(self) -> None:
        """Load voices or pre-connect the selected provider."""
        return None

    def close(self) -> None:
        """Release provider resources."""
        return None

    def cue(self) -> bool:
        """Play a short, language-neutral cue before microphone capture."""
        return True

    def begin_utterance(self, language: str = "en") -> bool:
        """Start an optional multi-segment synthesis context.

        Providers that return True must also implement ``speak_segment`` and
        ``end_utterance``. The default keeps existing sentence-at-a-time TTS.
        """
        return False

    def speak_segment(self, text: str, language: str = "en") -> bool:
        """Queue one segment in an active multi-segment synthesis context."""
        return self.speak(text, language)

    def end_utterance(self) -> bool:
        """Finish an active multi-segment synthesis context."""
        return True

    def abort_utterance(self) -> None:
        """Cancel an active multi-segment synthesis context."""
        return None

    @abstractmethod
    def speak(self, text: str, language: str = "en") -> bool:
        """Synthesise text and play it through the audio output.

        Returns True if audio was produced, False on failure. Callers must
        treat False as "fall back to showing the answer as text" — never
        crash the cycle because TTS failed.
        """
        ...
