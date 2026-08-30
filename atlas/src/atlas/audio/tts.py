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

    def set_output_device(self, output_device_name: str) -> None:
        """Route future playback without changing the microphone input."""
        return None

    def set_volume(self, volume_percent: int) -> None:
        """Set software playback gain for future output."""
        return None

    def audio_settings(self) -> dict[str, object]:
        """Return privacy-safe playback settings for the admin dashboard."""
        return {}

    def test_sound(self) -> bool:
        """Play the local cue through the currently selected output."""
        return self.cue()

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
