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
        self.output_device_name = "initial"
        self.volume_percent = 100

    def warm_up(self) -> None:
        return None

    def begin_utterance(self, language: str = "en") -> bool:
        return self.streams

    def speak(self, text: str, language: str = "en") -> bool:
        self.spoken.append(text)
        result = self.answers.pop(0) if self.answers else True
        self.playback_started = result
        return result

    def set_output_device(self, output_device_name: str) -> None:
        self.output_device_name = output_device_name

    def set_volume(self, volume_percent: int) -> None:
        self.volume_percent = volume_percent


class LateFailingStreamTTS(FakeTTS):
    """A continuous provider that reports failure after accepting audio."""

    def __init__(self) -> None:
        super().__init__([], streams=True)

    def speak_segment(self, text: str, language: str = "en") -> bool:
        self.spoken.append(text)
        return True

    def end_utterance(self) -> bool:
        return False


def test_non_streaming_fallback_synthesizes_one_complete_answer() -> None:
    primary = FakeTTS([False])
    fallback = FakeTTS([True])
    tts = FallbackTTS(primary, fallback)
    tts.warm_up()

    assert tts.begin_utterance("en") is True
    assert tts.speak_segment("First sentence.", "en") is True
    assert tts.speak_segment("Second sentence.", "en") is True
    assert tts.end_utterance() is True

    assert primary.spoken == []
    assert fallback.spoken == ["First sentence. Second sentence."]
    assert tts.last_provider == "FakeTTS"


def test_audio_controls_propagate_to_primary_and_fallback() -> None:
    primary = FakeTTS([True])
    fallback = FakeTTS([True])
    tts = FallbackTTS(primary, fallback)
    tts.warm_up()

    tts.set_output_device("Judge speaker")
    tts.set_volume(72)

    assert primary.output_device_name == "Judge speaker"
    assert fallback.output_device_name == "Judge speaker"
    assert primary.volume_percent == 72
    assert fallback.volume_percent == 72


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
