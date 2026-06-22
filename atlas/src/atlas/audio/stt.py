"""Abstract STT interface and TranscriptResult dataclass."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TranscriptResult:
    text: str
    language: str = "en"       # ISO-639-1 code
    confidence: float = 1.0
    age_hint: str = "adult"    # "child" | "teen" | "adult"


class BaseSTT(ABC):
    @abstractmethod
    def listen(self, duration_s: float = 5.0) -> Optional[TranscriptResult]:
        """
        Record up to duration_s seconds and return a transcript.
        Returns None if nothing captured or recognition failed.
        """
        ...
