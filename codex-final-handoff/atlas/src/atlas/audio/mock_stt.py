"""Mock STT — cycles canned bilingual questions, no microphone needed."""
from __future__ import annotations
from typing import Optional
from .stt import BaseSTT, TranscriptResult

_CANNED: list[TranscriptResult] = [
    TranscriptResult(text="Who painted this?",             language="en", age_hint="adult"),
    TranscriptResult(text="When was this created?",         language="en", age_hint="teen"),
    TranscriptResult(text="Qu'est-ce que ca represente?",  language="fr", age_hint="adult"),
    TranscriptResult(text="Why are the colours so dark?",   language="en", age_hint="child"),
    TranscriptResult(text="C'est qui l'artiste?",           language="fr", age_hint="teen"),
]


class MockSTT(BaseSTT):
    """Cycles through canned questions. No microphone or network required."""

    def __init__(self) -> None:
        self._idx = 0

    def listen(self, duration_s: float = 5.0) -> Optional[TranscriptResult]:
        result = _CANNED[self._idx % len(_CANNED)]
        self._idx += 1
        return result
