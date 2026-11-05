"""Verify actual synthesis controls without cloud calls, voices or audio devices."""

from __future__ import annotations

import base64
import io
import json
import queue
from pathlib import Path
from types import SimpleNamespace

import pytest

from atlas.app.dependency_container import Container
from atlas.audio.cartesia_tts import CartesiaTTS
from atlas.audio.fallback import FallbackTTS
from atlas.audio.mock_tts import MockTTS
from atlas.audio.piper_tts import PiperTTS
from atlas.audio.speech_pace import SpeechPace, apply_speech_pace
from atlas.config.settings import Settings, SpeechSettings
from tests.test_intro_before_artwork_invitation import make_visit
from tests.test_pipeline import _make_runner


class Socket:
    def __init__(self):
        self.sent = []
        self.messages = queue.Queue()

    def send(self, raw):
        request = json.loads(raw)
        self.sent.append(request)
        if request["transcript"]:
            self.messages.put(
                json.dumps(
                    {
                        "type": "chunk",
                        "context_id": request["context_id"],
                        "data": base64.b64encode(b"\0\0").decode(),
                    }
                )
            )
        if not request["continue"]:
            self.messages.put(
                json.dumps(
                    {
                        "type": "done",
                        "context_id": request["context_id"],
                    }
                )
            )

    def recv(self, timeout):
        return self.messages.get(timeout=timeout)


def cloud(monkeypatch):
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.open_raw_player",
        lambda *_a: SimpleNamespace(stdin=io.BytesIO()),
    )
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.finish_raw_player", lambda *_a, **_k: True
    )
    tts = CartesiaTTS(voice_id="synthetic-unchanged-voice")
    tts._connection = Socket()
    return tts


@pytest.mark.parametrize("slow,expected", [(False, 0.90), (True, 0.80)])
@pytest.mark.parametrize("streaming", [False, True])
def test_cartesia_whole_and_streamed_requests_have_explicit_pace(
    monkeypatch,
    slow,
    expected,
    streaming,
):
    tts = cloud(monkeypatch)
    tts.set_slower_pace(slow)
    if streaming:
        assert tts.begin_utterance("fr")
        assert tts.speak_segment("Une explication simple.", "fr")
        # A new preference cannot change the current answer halfway through.
        tts.set_slower_pace(not slow)
        assert tts.speak_segment("Une seconde phrase.", "fr")
        assert tts.end_utterance()
    else:
        assert tts.speak("Une explication simple.", "fr")
    assert all(
        r["generation_config"] == {"speed": expected} for r in tts._connection.sent
    )
    assert all(
        r["voice"] == {"mode": "id", "id": "synthetic-unchanged-voice"}
        for r in tts._connection.sent
    )
    assert all(r["output_format"]["sample_rate"] == 24000 for r in tts._connection.sent)
    if streaming:
        assert tts.speak("Une nouvelle réponse.", "fr")
        assert tts._connection.sent[-1]["generation_config"]["speed"] == (
            0.90 if slow else 0.80
        )


@pytest.mark.parametrize("private", [False, True])
def test_piper_synthesis_uses_inverse_speed_and_resets_between_visits(
    monkeypatch, private
):
    tts = PiperTTS("synthetic-en", "synthetic-fr")
    tts._command = ["synthetic-piper"]
    commands = []

    def run(command, **_kwargs):
        commands.append(command)
        Path(command[command.index("--output-file") + 1]).write_bytes(b"synthetic wav")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(tts, "_run_process", run)
    monkeypatch.setattr(tts, "_play_wav", lambda *_a, **_k: True)
    speak = tts.speak_private_local if private else tts.speak
    for slow, expected in [(False, 10 / 9), (True, 5 / 4), (False, 10 / 9)]:
        tts.set_slower_pace(slow)
        assert speak("Bonjour.", "fr")
        command = commands[-1]
        assert float(command[command.index("--length-scale") + 1]) == pytest.approx(
            expected
        )
        assert command[command.index("--model") + 1] == "synthetic-fr"


@pytest.mark.parametrize(
    "profile",
    [
        "early_child",
        "child",
        "teen",
        "adult_beginner",
        "expert",
        "visual_impairment",
        "simple_language",
    ],
)
@pytest.mark.parametrize(
    "choices,slow",
    [
        ([], False),
        (["simple_language"], False),
        (["audio_description"], False),
        (["slower_pace"], True),
        (["slower_pace", "simple_language", "audio_description"], True),
    ],
)
def test_only_explicit_slow_option_changes_provider_pace(profile, choices, slow):
    primary = CartesiaTTS(voice_id="synthetic")
    local = PiperTTS("synthetic-en", "synthetic-fr")
    tts = FallbackTTS(primary, local)
    runner = _make_runner(tts=tts)
    runner.set_preferred_profile(profile)
    runner.set_preferred_accessibility(choices)
    assert primary._pace.speed == local._pace.speed == (0.80 if slow else 0.90)
    runner.set_preferred_accessibility([])
    assert primary._pace.speed == local._pace.speed == 0.90


@pytest.mark.parametrize("named", [False, True])
def test_wake_greeting_gets_the_visit_pace_and_next_visit_drops_it(named):
    _container, service, speech = make_visit("Synthetic" if named else None)
    selected = []
    speech.set_slower_pace = selected.append
    service.set_profile(accessibility=["slower_pace", "simple_language"])
    assert service.activate_from_wake("Bonjour Atlas")
    assert service.speak_pending_greeting()
    assert selected == [True]
    service.stop_session()
    service.start_session(demo=True)
    assert service.activate_from_wake("Bonjour Atlas")
    assert service.speak_pending_greeting()
    assert selected == [True, False]


def test_existing_saved_settings_without_speed_keys_use_new_defaults():
    settings = SpeechSettings.model_validate({"cartesia_model": "sonic-3.5"})
    assert settings.tts_speed == 0.90
    assert settings.tts_slower_speed == 0.80
    assert (
        settings.silero_min_silence_ms,
        settings.silero_hesitation_silence_ms,
        settings.silero_scripted_faq_silence_ms,
    ) == (500, 1000, 300)


def test_device_container_wires_both_providers_to_configured_speeds():
    settings = Settings(
        mode="device",
        speech=SpeechSettings(
            tts_provider="cartesia",
            cloud_speech_enabled=True,
            tts_speed=0.93,
            tts_slower_speed=0.77,
        ),
    )
    tts = Container(settings).tts
    assert isinstance(tts, FallbackTTS)
    assert tts.primary._pace.normal == tts.fallback._pace.normal == 0.93
    tts.set_slower_pace(True)
    assert tts.primary._pace.speed == tts.fallback._pace.speed == 0.77


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 0.0, 0.59, 1.51])
def test_invalid_speed_is_rejected_by_settings_and_adapters(value):
    with pytest.raises(ValueError):
        SpeechSettings(tts_speed=value)
    with pytest.raises(ValueError):
        SpeechPace(value, 0.6)


def test_slow_option_cannot_be_faster_than_normal():
    with pytest.raises(ValueError):
        SpeechSettings(tts_speed=0.8, tts_slower_speed=0.9)
    with pytest.raises(ValueError):
        SpeechPace(0.8, 0.9)


def test_legacy_and_mock_adapters_remain_usable():
    apply_speech_pace(object(), ["slower_pace"])
    tts = MockTTS()
    apply_speech_pace(tts, ["slower_pace"])
    assert tts.slower_pace
    apply_speech_pace(tts, ["simple_language"])
    assert not tts.slower_pace
