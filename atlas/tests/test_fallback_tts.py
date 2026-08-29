"""Focused tests for keeping one audible voice per streamed response."""
from __future__ import annotations

from atlas.audio.fallback import FallbackTTS
from atlas.audio.tts import BaseTTS


class FakeTTS(BaseTTS):
    def __init__(self, answers: list[bool], *, streams: bool = False) -> None:
        self.answers = list(answers)
        self.streams = streams
        self.spoken: list[str] = []
        self.playback_started = False

    def warm_up(self) -> None:
        return None

    def begin_utterance(self, language: str = "en") -> bool:
        return self.streams

    def speak(self, text: str, language: str = "en") -> bool:
        self.spoken.append(text)
        result = self.answers.pop(0) if self.answers else True
        self.playback_started = result
        return result


class LateFailingStreamTTS(FakeTTS):
    """A continuous provider that reports failure after accepting audio."""

    def __init__(self) -> None:
        super().__init__([], streams=True)

    def speak_segment(self, text: str, language: str = "en") -> bool:
        self.spoken.append(text)
        return True

    def end_utterance(self) -> bool:
        return False


def test_response_lock_moves_to_fallback_only_before_any_audio() -> None:
    primary = FakeTTS([False])
    fallback = FakeTTS([True, True])
    tts = FallbackTTS(primary, fallback)
    tts.warm_up()

    assert tts.begin_utterance("en") is False
    assert tts.speak("First sentence.", "en") is True
    assert tts.speak("Second sentence.", "en") is True

    assert primary.spoken == ["First sentence."]
    assert fallback.spoken == ["First sentence.", "Second sentence."]
    assert tts.last_provider == "FakeTTS"


def test_response_lock_never_switches_after_audio_has_started() -> None:
    primary = FakeTTS([True, False])
    fallback = FakeTTS([True])
    tts = FallbackTTS(primary, fallback)
    tts.warm_up()

    assert tts.begin_utterance("en") is False
    assert tts.speak("First sentence.", "en") is True
    assert tts.speak("Second sentence.", "en") is False

    assert primary.spoken == ["First sentence.", "Second sentence."]
    assert fallback.spoken == []


def test_continuous_failure_never_replays_answer_with_another_voice() -> None:
    primary = LateFailingStreamTTS()
    fallback = FakeTTS([True])
    tts = FallbackTTS(primary, fallback)
    tts.warm_up()

    assert tts.begin_utterance("en") is True
    assert tts.speak_segment("First sentence.", "en") is True
    assert tts.speak_segment("Second sentence.", "en") is True
    assert tts.end_utterance() is False

    assert primary.spoken == ["First sentence.", "Second sentence."]
    assert fallback.spoken == []
