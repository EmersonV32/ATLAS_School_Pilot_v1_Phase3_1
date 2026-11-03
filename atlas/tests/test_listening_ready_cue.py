"""Readiness sounds must follow successful input opening, never replace speech."""

from __future__ import annotations

import json
import struct
import sys
import threading
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from atlas.app.dependency_container import Container
from atlas.audio.cartesia_tts import CartesiaTTS
from atlas.audio.deepgram_stt import DeepgramError, DeepgramSTT
from atlas.audio.fallback import FallbackSTT, FallbackTTS
from atlas.audio.mock_stt import MockSTT
from atlas.audio.mock_tts import MockTTS
from atlas.audio.piper_tts import PiperTTS
from atlas.audio.playback import ready_cue_pcm
from atlas.audio.stt import TranscriptResult
from atlas.audio.whisper_stt import WhisperSTT
from atlas.config.settings import Settings, SpeechSettings
from atlas.dashboard.schemas import SpeechConfigUpdate
from atlas.dialogue.dialogue_engine import DialogueEngine
from atlas.dialogue.mock_llm_client import MockLLMClient
from atlas.hardware.mock_hardware import MockHardware
from atlas.models.enums import RunMode
from atlas.pipeline.session_runner import SessionRunner
from atlas.vision.mock_detector import MockDetector


class ReadySTT(MockSTT):
    def __init__(self, events, answers):
        super().__init__()
        self.events = events
        self.answers = iter(answers)
        self.callback = None
        self.microphone_open = False
        self.fail_prepare = False
        self.fail_open = False
        self.during_prepare = None
        self.before_ready = None

    def set_ready_callback(self, callback):
        self.callback = callback
        return True

    def prepare_listen(self):
        self.events.append("prepare")
        if self.during_prepare:
            self.during_prepare()
        if self.fail_prepare:
            raise OSError("synthetic connection failure")

    def listen(self, duration_s=5.0):
        if self.fail_open:
            raise OSError("synthetic input-open failure")
        self.microphone_open = True
        self.events.append("input-open")
        try:
            if self.before_ready:
                self.before_ready()
            if self.callback:
                self.callback()
                self.callback()  # A duplicate notification must not double-cue.
            return next(self.answers)
        finally:
            self.microphone_open = False
            self.events.append("input-close")


class RecordingTTS(MockTTS):
    def __init__(self, events, is_open):
        super().__init__()
        self.events = events
        self.is_open = is_open
        self.failure = None

    def cue(self):
        self.events.append("legacy-cue")
        return True

    def ready_cue(self, style="buzz"):
        assert self.is_open(), "A readiness sound preceded microphone opening"
        self.events.append("ready:" + style)
        if self.failure == "raise":
            raise OSError("synthetic sound failure")
        return self.failure != "false"


def runner_for(stt, events, style="buzz", is_open=None):
    tts = RecordingTTS(events, is_open or (lambda: stt.microphone_open))
    runner = SessionRunner(
        detector=MockDetector(),
        stt=stt,
        tts=tts,
        hardware=MockHardware(),
        dialogue_engine=DialogueEngine(MockLLMClient()),
        retriever=lambda *_: [],
        listening_ready_cue=style,
    )
    return runner, tts


@pytest.mark.parametrize("style", ["buzz", "beep"])
def test_start_and_each_followup_sound_only_after_input_opens(style):
    events = []
    questions = ["Who painted the Mona Lisa?", "How was it painted?"]
    stt = ReadySTT(events, [TranscriptResult(q) for q in questions])
    runner, _tts = runner_for(stt, events, style)
    runner.cue_listening()
    assert events == []
    for question in questions:
        assert runner.listen_once().text == question
    assert events == ["prepare", "input-open", "ready:" + style, "input-close"] * 2
    stt.callback()  # A late callback outside capture must also remain silent.
    assert len([e for e in events if e.startswith("ready:")]) == 2


def test_idle_capture_timeouts_do_not_repeat_the_sound():
    events = []
    question = TranscriptResult("Explain these colours.")
    stt = ReadySTT(events, [None, None, question, None])
    runner, _tts = runner_for(stt, events)
    assert runner.listen_once() is None
    assert runner.listen_once() is None
    assert events.count("ready:buzz") == 1
    assert runner.listen_once().text == question.text
    assert events.count("ready:buzz") == 1
    assert runner.listen_once() is None
    assert events.count("ready:buzz") == 2


def test_off_setting_preserves_question_without_registering_or_playing_sound():
    events = []
    stt = ReadySTT(events, [TranscriptResult("Who painted this?")])
    runner, _tts = runner_for(stt, events, "off")
    runner.cue_listening()
    assert stt.callback is None
    assert runner.listen_once(play_cue=True).text == "Who painted this?"
    assert events == ["prepare", "input-open", "input-close"]


@pytest.mark.parametrize("style", [None, "off"])
def test_reused_adapter_cannot_keep_a_previous_runners_ready_callback(style):
    events = []
    stt = ReadySTT(events, [TranscriptResult("Current question")])
    stt.set_ready_callback(lambda: events.append("stale-ready"))
    runner, _tts = runner_for(stt, events, style)
    assert stt.callback is None
    assert runner.listen_once().text == "Current question"
    assert "stale-ready" not in events


@pytest.mark.parametrize("when", ["prepare", "input-open"])
def test_cancelled_capture_cannot_announce_readiness_or_return_old_speech(when):
    events = []
    stt = ReadySTT(events, [TranscriptResult("old question")])
    runner, _tts = runner_for(stt, events)
    if when == "prepare":
        stt.during_prepare = runner.cancel_listening
    else:
        stt.before_ready = runner.cancel_listening
    assert runner.listen_once() is None
    assert "ready:buzz" not in events


def test_failed_input_open_has_no_ready_sound():
    events = []
    stt = ReadySTT(events, [TranscriptResult("must not be returned")])
    stt.fail_open = True
    runner, _tts = runner_for(stt, events)
    assert runner.listen_once() is None
    assert events == ["prepare"]


@pytest.mark.parametrize("failure", ["raise", "false"])
def test_sound_failure_does_not_drop_the_immediate_question(failure):
    events = []
    stt = ReadySTT(events, [TranscriptResult("Keep the entire first word.")])
    runner, tts = runner_for(stt, events)
    tts.failure = failure
    assert runner.listen_once().text == "Keep the entire first word."
    assert events.count("ready:buzz") == 1


@pytest.mark.parametrize("use_fallback", [False, True])
def test_stt_fallback_notifies_for_the_provider_that_really_opens(use_fallback):
    events = []
    primary = ReadySTT(events, [TranscriptResult("primary question")])
    fallback = ReadySTT(events, [TranscriptResult("fallback question")])
    primary.fail_prepare = use_fallback
    stt = FallbackSTT(primary, fallback)
    stt.primary_ready = stt.fallback_ready = True
    runner, _tts = runner_for(
        stt,
        events,
        is_open=lambda: primary.microphone_open or fallback.microphone_open,
    )
    expected = "fallback question" if use_fallback else "primary question"
    assert runner.listen_once().text == expected
    assert events.count("ready:buzz") == 1


@pytest.mark.parametrize("fail_open", [False, True])
def test_deepgram_notifies_after_stream_enter_and_before_first_frame(
    monkeypatch, fail_open
):
    events = []
    state = SimpleNamespace(messages=None, receiver_ready=threading.Event())

    class VAD:
        threshold = 0.5

        def reset(self):
            self.reads = 0

        def probability(self, _pcm):
            self.reads += 1
            return 1.0 if self.reads == 1 else 0.0

    class Connection:
        def send(self, payload):
            if isinstance(payload, str) and json.loads(payload)["type"] == "Finalize":
                state.messages.put(
                    {
                        "type": "Results",
                        "is_final": True,
                        "from_finalize": True,
                        "start": 0,
                        "duration": 1,
                        "channel": {
                            "alternatives": [{"transcript": "First word stays."}]
                        },
                    }
                )

        def close(self):
            pass

    class Stream:
        def __enter__(self):
            if fail_open:
                raise OSError("synthetic input-open failure")
            assert state.receiver_ready.wait(1)
            events.append("input-open")
            return self

        def __exit__(self, *_args):
            events.append("input-close")

        def read(self, count):
            assert events[:2] == ["input-open", "ready"]
            events.append("frame")
            return b"\x01\0" * count, False

    stt = DeepgramSTT(
        vad=VAD(),
        keep_connection_enabled=False,
        min_speech_ms=0,
        min_silence_ms=0,
    )
    stt._ready = True
    stt._prepared_connection = Connection()
    stt.set_ready_callback(lambda: events.append("ready"))

    def receiver(_connection, messages, **_kwargs):
        state.messages = messages
        state.receiver_ready.set()

    monkeypatch.setattr(stt, "_receiver", receiver)
    monkeypatch.setitem(
        sys.modules, "sounddevice", SimpleNamespace(RawInputStream=lambda **_: Stream())
    )
    if fail_open:
        with pytest.raises(DeepgramError):
            stt.listen()
        assert events == []
    else:
        assert stt.listen().text == "First word stays."
        assert events.count("ready") == 1


@pytest.mark.parametrize("fail_open", [False, True])
def test_whisper_cue_requires_successful_recording_start(monkeypatch, fail_open):
    events = []

    def record(*_args, **_kwargs):
        if fail_open:
            raise OSError("synthetic input-open failure")
        events.append("input-open")
        return [0.0]

    stt = WhisperSTT()
    stt._model = object()
    stt.set_ready_callback(lambda: events.append("ready"))
    monkeypatch.setattr(
        stt, "_transcribe", lambda *_a, **_kw: TranscriptResult("Full question")
    )
    monkeypatch.setitem(
        sys.modules,
        "sounddevice",
        SimpleNamespace(
            rec=record,
            wait=lambda: events.append("wait"),
        ),
    )
    answer = stt.listen()
    if fail_open:
        assert answer is None
        assert events == []
    else:
        assert answer.text == "Full question"
        assert events == ["input-open", "ready", "wait"]


@pytest.mark.parametrize("provider", ["cartesia", "piper"])
@pytest.mark.parametrize("style", ["off", "buzz", "beep"])
def test_local_ready_sound_uses_selected_output_and_bounded_playback(
    monkeypatch, provider, style
):
    calls = []
    monkeypatch.setattr(
        f"atlas.audio.{provider}_tts.play_pcm",
        lambda pcm, output, **kw: calls.append((pcm, output, kw)) or True,
    )
    adapter = (
        CartesiaTTS(
            voice_id="synthetic", output_device_name="Chosen output", volume_percent=35
        )
        if provider == "cartesia"
        else PiperTTS(
            voice_en="unused",
            voice_fr="unused",
            output_device_name="Chosen output",
            volume_percent=35,
        )
    )
    assert adapter.ready_cue(style)
    if style == "off":
        assert calls == []
    else:
        pcm, output, options = calls[0]
        assert pcm == ready_cue_pcm(style)
        assert output == "Chosen output"
        assert options == {"sample_rate": 16000, "volume_percent": 35, "timeout_s": 1.0}


@pytest.mark.parametrize("primary_ready", [False, True])
def test_tts_fallback_routes_sound_to_available_provider(primary_ready):
    calls = []
    primary, fallback = MockTTS(), MockTTS()
    primary.ready_cue = lambda style: calls.append(("primary", style)) or True
    fallback.ready_cue = lambda style: calls.append(("fallback", style)) or True
    adapter = FallbackTTS(primary, fallback)
    adapter.primary_ready = primary_ready
    assert adapter.ready_cue("buzz")
    assert calls == [("primary" if primary_ready else "fallback", "buzz")]


@pytest.mark.parametrize("rate", [8000, 16000, 24000])
@pytest.mark.parametrize("style", ["buzz", "beep"])
def test_generated_sound_is_short_bounded_and_fades_at_both_edges(rate, style):
    pcm = ready_cue_pcm(style, sample_rate=rate)
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    assert len(samples) == rate * 8 // 100
    assert len(pcm) / (2 * rate) == pytest.approx(0.08)
    assert samples[0] == samples[-1] == 0
    assert 500 < max(abs(value) for value in samples) <= 3500


def test_sounds_are_distinct_and_off_generates_no_audio():
    assert ready_cue_pcm("buzz") != ready_cue_pcm("beep")
    assert ready_cue_pcm("off") == b""
    with pytest.raises(ValueError):
        ready_cue_pcm("unsupported")


def test_legacy_tts_adapter_falls_back_to_its_beep_and_honors_off():
    calls = []
    adapter = MockTTS()
    adapter.cue = lambda: calls.append("legacy-beep") or True
    assert adapter.ready_cue("buzz")
    assert adapter.ready_cue("off")
    assert calls == ["legacy-beep"]


@pytest.mark.parametrize("style", ["off", "buzz", "beep"])
def test_readiness_style_is_selectable_without_disabling_connection_reuse(style):
    settings = SpeechSettings(listening_ready_cue=style)
    update = SpeechConfigUpdate(listening_ready_cue=style)
    assert settings.deepgram_keep_connection is True
    assert settings.listening_ready_cue == update.listening_ready_cue == style
    with pytest.raises(ValidationError):
        SpeechConfigUpdate(listening_ready_cue="unsupported")


@pytest.mark.parametrize("keep_connection", [False, True])
@pytest.mark.parametrize("style", ["off", "buzz", "beep"])
def test_device_factory_wires_connection_choice_and_actual_ready_sound(
    monkeypatch, keep_connection, style
):
    events, constructed = [], []

    class DeviceSTT(ReadySTT):
        def __init__(self, **options):
            super().__init__(events, [TranscriptResult("First word stays.")])
            constructed.append(options)

    monkeypatch.setattr("atlas.audio.deepgram_stt.DeepgramSTT", DeviceSTT)
    container = Container(
        Settings(
            mode=RunMode.DEVICE,
            speech=SpeechSettings(
                stt_provider="deepgram",
                cloud_speech_enabled=True,
                offline_fallback_enabled=False,
                deepgram_keep_connection=keep_connection,
                listening_ready_cue=style,
            ),
        )
    )
    container._artwork_tracker = MockDetector()
    container._tts = RecordingTTS(events, lambda: container.stt.microphone_open)
    container._hardware = MockHardware()
    container._dialogue_engine = DialogueEngine(MockLLMClient())
    container._retriever = SimpleNamespace()
    container._manual_artwork_capture = object()
    runner = container.session_runner
    assert constructed[0]["keep_connection_enabled"] is keep_connection
    runner.cue_listening()
    assert events == []
    assert runner.listen_once().text == "First word stays."
    assert [e for e in events if e.startswith("ready:")] == (
        [] if style == "off" else ["ready:" + style]
    )
