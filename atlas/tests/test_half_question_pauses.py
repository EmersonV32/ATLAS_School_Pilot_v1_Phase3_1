"""Measure endpoint waits on synthetic PCM, not network or headset latency."""

import pytest

from atlas.audio.deepgram_stt import DeepgramSTT
from atlas.config.settings import SpeechSettings
from tests.test_listening_workflow import capture, result_payload


def timing_options():
    s = SpeechSettings()
    return dict(
        min_silence_ms=s.silero_min_silence_ms,
        hesitation_silence_ms=s.silero_hesitation_silence_ms,
        scripted_faq_silence_ms=s.silero_scripted_faq_silence_ms,
    )


def test_all_three_constructor_waits_are_half_the_previous_release():
    stt = DeepgramSTT()
    assert stt._min_silence_ms * 2 == 1000
    assert stt._hesitation_silence_ms * 2 == 2000
    assert stt._scripted_faq_silence_ms * 2 == 600


@pytest.mark.parametrize(
    ("question", "low", "high"),
    [
        ("Explain the arrangement of colours.", 0.5, 0.55),
        ("Who painted", 1.0, 1.05),
        ("Who painted the Mona Lisa?", 0.3, 0.38),
    ],
)
def test_halved_waits_on_actual_synthetic_capture(monkeypatch, question, low, high):
    result, _state, clock = capture(
        monkeypatch,
        [(0.5, True), (5, False)],
        **timing_options(),
        live_payloads={17: [result_payload(question, duration=0.512)]},
        payloads=[result_payload("", flush=True)],
    )
    assert result.text == question
    assert low <= clock.now - result.speech_end_monotonic_s < high


def test_resumed_voice_still_invalidates_a_late_prepared_final_at_shorter_waits(
    monkeypatch,
):
    result, state, clock = capture(
        monkeypatch,
        [(0.5, True), (0.16, False), (0.5, True), (5, False)],
        **timing_options(),
        live_payloads={
            27: [result_payload("Who painted the Mona Lisa?", duration=0.512)]
        },
        payloads=[result_payload("and why", start=0.512, duration=0.8, flush=True)],
    )
    assert state.reads * 0.032 > 1.6
    assert "and why" in result.text
    assert clock.now - result.speech_end_monotonic_s >= 0.5
