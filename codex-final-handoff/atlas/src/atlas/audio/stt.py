"""Abstract STT interface and TranscriptResult dataclass."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptResult:
    text: str
    language: str = "en"       # ISO-639-1 code
    confidence: float = 1.0
    age_hint: str = "adult"    # "child" | "teen" | "adult"
    duration_ms: float | None = None  # STT latency, for telemetry


class BaseSTT(ABC):
    def warm_up(self) -> None:
        """Load local models and validate provider dependencies."""
        return None

    def close(self) -> None:
        """Release provider resources."""
        return None

    def prepare_listen(self) -> None:
        """Prepare a provider immediately before the listening cue."""
        return None

    def set_language(self, language: str) -> None:
        """Prefer one ISO-639-1 language for the next listening cycle."""
        return None

    @abstractmethod
    def listen(self, duration_s: float = 5.0) -> TranscriptResult | None:
        """
        Record up to duration_s seconds and return a transcript.
        Returns None if nothing captured or recognition failed.
        """
        ...
