"""Focused tests for keeping one audible voice per streamed response."""
from __future__ import annotations

import threading

import pytest

from atlas.audio.fallback import FallbackTTS
from atlas.audio.tts import BaseTTS
from atlas.models.languages import ADMIN_LANGUAGE_CODES


class FakeTTS(BaseTTS):
    def __init__(self, answers: list[bool], *, streams: bool = False) -> None:
        self.answers = list(answers)
        self.streams = streams
        self.spoken: list[str] = []
        self.playback_started = False
        self.output_device_name = "initial"
        self.volume_percent = 100
        self.warm_up_calls = 0

    def warm_up(self) -> None:
        self.warm_up_calls += 1

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


def test_transient_failure_recovers_primary_between_answers(monkeypatch) -> None:
    clock = [100.0]
    monkeypatch.setattr("atlas.audio.fallback.time.monotonic", lambda: clock[0])
    primary = FakeTTS([False, True])
    fallback = FakeTTS([True, True])
    tts = FallbackTTS(primary, fallback, primary_retry_interval_s=15)
    tts.warm_up()
    assert tts.speak("First answer", "fr") is True
    assert tts.primary_ready is False
    clock[0] = 110
    assert tts.speak("Second answer", "fr") is True
    assert primary.warm_up_calls == 1
    clock[0] = 115
    assert tts.speak("Third answer", "fr") is True
    assert primary.warm_up_calls == 2
    assert tts.primary_ready is True
    assert primary.spoken == ["First answer", "Third answer"]
    assert fallback.spoken == ["First answer", "Second answer"]


def test_primary_recovery_is_bounded_when_cloud_remains_offline(monkeypatch) -> None:
    clock = [100.0]
    monkeypatch.setattr("atlas.audio.fallback.time.monotonic", lambda: clock[0])

    class OfflineTTS(FakeTTS):
        def warm_up(self) -> None:
            super().warm_up()
            raise RuntimeError("synthetic offline")

    primary = OfflineTTS([])
    fallback = FakeTTS([])
    tts = FallbackTTS(primary, fallback, primary_retry_interval_s=15)
    tts.warm_up()
    assert tts.speak("First", "en") is True
    assert primary.warm_up_calls == 1
    clock[0] = 115
    assert tts.speak("Second", "en") is True
    assert primary.warm_up_calls == 2
    clock[0] = 116
    assert tts.speak("Third", "en") is True
    assert primary.warm_up_calls == 2


def test_primary_recovery_also_applies_before_continuous_answer(monkeypatch) -> None:
    clock = [100.0]
    monkeypatch.setattr("atlas.audio.fallback.time.monotonic", lambda: clock[0])
    primary = FakeTTS([False], streams=True)
    fallback = FakeTTS([True])
    tts = FallbackTTS(primary, fallback, primary_retry_interval_s=15)
    tts.warm_up()
    assert tts.speak("Failed primary answer", "fr") is True
    assert tts.primary_ready is False
    clock[0] = 115
    assert tts.begin_utterance("fr") is True
    assert primary.warm_up_calls == 2
    assert tts.primary_ready is True
    assert tts._locked_adapter is primary
    assert fallback.spoken == ["Failed primary answer"]


@pytest.mark.parametrize("language", sorted(ADMIN_LANGUAGE_CODES))
def test_failure_after_audio_never_switches_provider(language) -> None:
    class AudibleFailure(FakeTTS):
        def speak(self, text: str, language: str = "en") -> bool:
            self.spoken.append(text)
            self.playback_started = True
            return False

    primary = AudibleFailure([])
    fallback = FakeTTS([])
    tts = FallbackTTS(primary, fallback)
    tts.warm_up()
    assert tts.speak("One complete answer", language) is False
    assert fallback.spoken == []


def test_queued_speech_is_cancelled_before_another_provider_call() -> None:
    entered = threading.Event()
    release = threading.Event()
    queued = threading.Event()

    class BlockingTTS(FakeTTS):
        def speak(self, text: str, language: str = "en") -> bool:
            self.spoken.append(text)
            entered.set()
            assert release.wait(timeout=3)
            self.playback_started = True
            return True

    primary = BlockingTTS([])
    fallback = FakeTTS([])
    tts = FallbackTTS(primary, fallback)
    tts.warm_up()

    class ObservedLock:
        def __init__(self):
            self.lock = threading.RLock()

        def __enter__(self):
            if threading.current_thread().name == "queued-speech":
                queued.set()
            self.lock.acquire()

        def __exit__(self, *args):
            self.lock.release()

    tts._speak_lock = ObservedLock()
    results = []
    first = threading.Thread(target=lambda: results.append(tts.speak("First")))
    first.start()
    assert entered.wait(timeout=3)

    second = threading.Thread(
        target=lambda: results.append(tts.speak("Queued")), name="queued-speech"
    )
    # The queued thread cannot reach the provider until the first call exits.
    second.start()
    assert queued.wait(timeout=3)
    tts.abort_utterance()
    release.set()
    first.join(timeout=3)
    second.join(timeout=3)
    assert not first.is_alive() and not second.is_alive()
    assert queued.is_set()
    assert results == [False, False]
    assert primary.spoken == ["First"]
    assert fallback.spoken == []
