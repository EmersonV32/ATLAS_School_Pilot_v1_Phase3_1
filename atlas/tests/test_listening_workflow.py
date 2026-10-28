"""No microphone/network: stream synthetic frames on a deterministic clock."""

import json
import sys
import threading
from types import SimpleNamespace

import pytest

from atlas.audio.deepgram_stt import (
    DeepgramError,
    DeepgramSTT,
    QuestionTranscript,
    question_needs_more_speech,
)
from atlas.audio.fallback import FallbackSTT
from atlas.audio.mock_stt import MockSTT
from atlas.config.settings import SpeechSettings


def result_payload(text, *, final=True, start=0, duration=1, flush=False):
    return {
        "type": "Results",
        "is_final": final,
        "speech_final": final,
        "from_finalize": flush,
        "start": start,
        "duration": duration,
        "channel": {
            "alternatives": [
                {
                    "transcript": text,
                    "confidence": 0.9,
                    "words": [],
                }
            ]
        },
    }


def capture(
    monkeypatch,
    segments,
    *,
    payloads=None,
    wait_s=8,
    live_payloads=None,
    cancel_at=None,
    fail_audio_at=None,
    failure_sink=None,
    **options,
):
    clock = SimpleNamespace(now=0.0)
    samples = [
        voice for seconds, voice in segments for _ in range(round(seconds / 0.032))
    ]
    state = SimpleNamespace(reads=0, sends=[], receiver_ready=threading.Event())

    class VAD:
        threshold = 0.5

        def reset(self):
            pass

        def probability(self, _pcm):
            return float(samples[min(state.reads - 1, len(samples) - 1)])

    class Connection:
        def send(self, payload):
            state.sends.append(payload)
            if isinstance(payload, bytes) and fail_audio_at is not None:
                if state.reads >= fail_audio_at:
                    raise OSError("synthetic connection failure")
            if isinstance(payload, str) and json.loads(payload)["type"] == "Finalize":
                for message in payloads or [
                    result_payload("A whole question", flush=True)
                ]:
                    state.messages.put(message)

        def close(self):
            pass

    class Stream:
        def __enter__(self):
            assert state.receiver_ready.wait(1)
            return self

        def __exit__(self, *_args):
            pass

        def read(self, count):
            state.reads += 1
            clock.now += 0.032
            for message in (live_payloads or {}).get(state.reads, []):
                state.messages.put(message)
            if state.reads == cancel_at:
                state.adapter.cancel_listen()
            return b"\x01\x00" * count, False

    stt = DeepgramSTT(vad=VAD(), **options)
    state.adapter = stt
    if failure_sink is not None:
        failure_sink["state"] = state
    stt._ready = True
    stt._prepared_connection = Connection()

    def receiver(_connection, messages, **_kwargs):
        state.messages = messages
        state.receiver_ready.set()

    monkeypatch.setattr(stt, "_receiver", receiver)
    monkeypatch.setattr(
        "atlas.audio.deepgram_stt.time",
        SimpleNamespace(monotonic=lambda: clock.now, perf_counter=lambda: clock.now),
    )
    monkeypatch.setitem(
        sys.modules,
        "sounddevice",
        SimpleNamespace(RawInputStream=lambda **_kw: Stream()),
    )
    answer = stt.listen(duration_s=wait_s)
    return answer, state, clock


def test_hesitation_does_not_end_recording_before_resumed_speech(monkeypatch):
    _answer, state, _clock = capture(
        monkeypatch, [(0.5, True), (1.5, False), (1, True), (3, False)]
    )
    assert state.reads * 0.032 >= 3


def test_question_starting_near_wait_timeout_is_not_cut_at_eight_seconds(monkeypatch):
    _answer, state, _clock = capture(monkeypatch, [(7.5, False), (4, True), (3, False)])
    assert state.reads * 0.032 >= 11.5


def test_unfinalized_tail_is_not_discarded_after_finalized_prefix(monkeypatch):
    answer, _state, _clock = capture(
        monkeypatch,
        [(0.5, True), (3, False)],
        payloads=[
            result_payload("Explain why", start=0, duration=1),
            result_payload("the sky swirls", final=False, start=1, duration=1),
            result_payload("", start=2, duration=0, flush=True),
        ],
    )
    assert answer.text == "Explain why the sky swirls"


def test_repeated_words_in_distinct_final_segments_are_not_deduplicated(monkeypatch):
    answer, _state, _clock = capture(
        monkeypatch,
        [(0.5, True), (3, False)],
        payloads=[
            result_payload("Why", start=0, duration=1),
            result_payload("Why", start=1, duration=1),
            result_payload("these colours?", start=2, duration=1, flush=True),
        ],
    )
    assert answer.text == "Why Why these colours?"


def test_server_speech_final_does_not_end_the_visitors_turn(monkeypatch):
    answer, state, _clock = capture(
        monkeypatch,
        [(0.5, True), (1.5, False), (1, True), (3, False)],
        live_payloads={12: [result_payload("Tell me about", duration=0.4)]},
        payloads=[result_payload("its colours", start=0.4, duration=3, flush=True)],
    )
    assert state.reads * 0.032 > 3
    assert answer.text == "Tell me about its colours"


def test_complete_question_uses_normal_pause_not_incomplete_question_grace(monkeypatch):
    _answer, state, clock = capture(
        monkeypatch,
        [(0.5, True), (5, False)],
        live_payloads={
            12: [result_payload("Why are the colours so vivid?", duration=0.4)]
        },
        payloads=[result_payload("", start=0.4, duration=0, flush=True)],
    )
    assert 2.4 <= clock.now < 2.7
    assert state.reads < 90


@pytest.mark.parametrize(
    ("question", "language"),
    [("Who painted the Mona Lisa?", "en"), ("Qui a peint la Joconde?", "fr")],
)
def test_exact_final_prepared_question_uses_stable_short_pause(
    monkeypatch, question, language
):
    answer, _state, clock = capture(
        monkeypatch,
        [(0.5, True), (5, False)],
        language=language,
        live_payloads={17: [result_payload(question, duration=0.512)]},
        payloads=[result_payload("", start=0.512, duration=0, flush=True)],
    )
    assert answer.text == question
    assert 1.1 <= clock.now < 1.2
    assert 0.6 <= clock.now - answer.speech_end_monotonic_s < 0.65
    assert answer.transcript_ready_monotonic_s == clock.now


def test_prepared_question_waits_for_final_receipt_stability(monkeypatch):
    _answer, _state, clock = capture(
        monkeypatch,
        [(0.5, True), (5, False)],
        live_payloads={36: [result_payload("Who painted the Mona Lisa?")]},
        payloads=[result_payload("", flush=True)],
    )
    assert 1.75 <= clock.now < 1.85


def test_duplicate_final_does_not_restart_prepared_question_stability(monkeypatch):
    final = result_payload("Who painted the Mona Lisa?", duration=0.512)
    _answer, _state, clock = capture(
        monkeypatch,
        [(0.5, True), (5, False)],
        live_payloads={17: [final], 25: [final]},
        payloads=[result_payload("", flush=True)],
    )
    assert 1.1 <= clock.now < 1.2


@pytest.mark.parametrize("continuation", ["interim", "voice"])
def test_continuation_invalidates_prepared_question_shortcut(monkeypatch, continuation):
    live = {17: [result_payload("Who painted the Mona Lisa?", duration=0.512)]}
    segments = [(0.5, True), (5, False)]
    if continuation == "interim":
        live[22] = [result_payload("and why", final=False, start=0.4, duration=0.4)]
    else:
        # No fresh transcript arrives: resumed VAD alone must invalidate it.
        segments = [(0.5, True), (0.3, False), (0.5, True), (5, False)]
    _answer, _state, clock = capture(
        monkeypatch,
        segments,
        live_payloads=live,
        payloads=[result_payload("", start=1, duration=0, flush=True)],
    )
    assert clock.now >= (2.5 if continuation == "interim" else 3.3)


@pytest.mark.parametrize("text", ["", "Who painted"])
def test_empty_or_stale_interim_does_not_invalidate_complete_final(monkeypatch, text):
    _answer, _state, clock = capture(
        monkeypatch,
        [(0.5, True), (5, False)],
        live_payloads={
            17: [result_payload("Who painted the Mona Lisa?", duration=0.512)],
            24: [result_payload(text, final=False, duration=0.2)],
        },
        payloads=[result_payload("", flush=True)],
    )
    assert 1.1 <= clock.now < 1.2


def test_delayed_old_final_cannot_rearm_shortcut_during_resumed_speech(monkeypatch):
    _answer, _state, clock = capture(
        monkeypatch,
        [(0.5, True), (0.3, False), (0.5, True), (5, False)],
        live_payloads={
            27: [result_payload("Who painted the Mona Lisa?", duration=0.512)]
        },
        payloads=[result_payload("and why", start=0.512, duration=0.8, flush=True)],
    )
    assert 3.3 <= clock.now < 3.5


@pytest.mark.parametrize("untimed", [False, True])
def test_final_must_cover_latest_sent_voiced_frame(monkeypatch, untimed):
    final = result_payload("Who painted the Mona Lisa?", duration=0.4)
    if untimed:
        del final["start"]
        del final["duration"]
    _answer, _state, clock = capture(
        monkeypatch,
        [(0.5, True), (5, False)],
        live_payloads={17: [final]},
        payloads=[result_payload("", flush=True)],
    )
    assert 2.4 <= clock.now < 2.7


def test_final_coverage_uses_sent_pcm_offsets_including_pre_roll(monkeypatch):
    answer, _state, clock = capture(
        monkeypatch,
        [(0.5, False), (0.5, True), (5, False)],
        live_payloads={
            33: [result_payload("Who painted the Mona Lisa?", duration=0.736)]
        },
        payloads=[result_payload("", flush=True)],
    )
    assert 1.6 <= clock.now < 1.7
    assert 0.6 <= clock.now - answer.speech_end_monotonic_s < 0.65


@pytest.mark.parametrize("final", [False, True])
def test_fuzzy_or_interim_prepared_question_keeps_general_pause(monkeypatch, final):
    question = "Who painted the Mna Lisa?" if final else "Who painted the Mona Lisa?"
    _answer, _state, clock = capture(
        monkeypatch,
        [(0.5, True), (5, False)],
        live_payloads={12: [result_payload(question, final=final, duration=0.4)]},
        payloads=[result_payload("", flush=True)],
    )
    assert 2.4 <= clock.now < 2.7


def test_prepared_question_shortcut_can_be_disabled(monkeypatch):
    _answer, _state, clock = capture(
        monkeypatch,
        [(0.5, True), (5, False)],
        scripted_faq_silence_ms=0,
        live_payloads={
            12: [result_payload("Who painted the Mona Lisa?", duration=0.4)]
        },
        payloads=[result_payload("", flush=True)],
    )
    assert 2.4 <= clock.now < 2.7


def test_existing_private_speech_settings_get_safe_prepared_question_default():
    settings = SpeechSettings.model_validate(
        {"silero_min_silence_ms": 2300, "silero_hesitation_silence_ms": 4500}
    )
    assert settings.silero_scripted_faq_silence_ms == 600
    assert settings.silero_min_silence_ms == 2300
    assert settings.silero_hesitation_silence_ms == 4500


def test_incomplete_question_allows_longer_hesitation_and_resumption(monkeypatch):
    answer, state, _clock = capture(
        monkeypatch,
        [(0.5, True), (3.1, False), (1, True), (5, False)],
        live_payloads={12: [result_payload("Who painted", duration=0.4)]},
        payloads=[result_payload("this painting?", start=0.4, duration=4, flush=True)],
    )
    assert state.reads * 0.032 > 4.5
    assert answer.text == "Who painted this painting?"


def test_quiet_wait_keeps_socket_alive_without_sending_microphone_audio(monkeypatch):
    answer, state, clock = capture(monkeypatch, [(8, False)])
    assert answer is None
    assert 8 <= clock.now < 8.1
    assert not any(isinstance(payload, bytes) for payload in state.sends)
    controls = [json.loads(payload)["type"] for payload in state.sends]
    assert controls == ["KeepAlive", "KeepAlive", "CloseStream"]


def test_maximum_utterance_remains_bounded_when_speech_never_stops(monkeypatch):
    answer, _state, clock = capture(monkeypatch, [(60, True)], max_utterance_s=5)
    assert answer is not None
    assert 5 <= clock.now < 5.1


def test_cancelled_capture_discards_audio_and_does_not_finalize_old_question(
    monkeypatch,
):
    answer, state, clock = capture(monkeypatch, [(60, True)], cancel_at=20)
    assert answer is None
    assert clock.now < 1
    assert state.adapter.last_audio_pcm == b""
    assert not any(
        isinstance(payload, str) and json.loads(payload)["type"] == "Finalize"
        for payload in state.sends
    )


def test_audio_send_failure_keeps_current_audio_for_local_recovery(monkeypatch):
    sink = {}
    with pytest.raises(DeepgramError, match="synthetic connection failure"):
        capture(monkeypatch, [(3, True)], fail_audio_at=20, failure_sink=sink)
    assert sink["state"].adapter.last_audio_pcm
    assert len(sink["state"].adapter.last_audio_pcm) == 20 * 512 * 2


def test_flush_can_finish_with_metadata_even_without_from_finalize_flag(monkeypatch):
    answer, _state, _clock = capture(
        monkeypatch,
        [(0.5, True), (5, False)],
        payloads=[result_payload("Full request"), {"type": "Metadata"}],
    )
    assert answer.text == "Full request"


def test_repeated_delivery_of_same_timed_segment_is_not_double_counted():
    transcript = QuestionTranscript("en")
    payload = result_payload("Why these colours?", start=0, duration=2)
    transcript.consume(payload)
    transcript.consume(payload)
    assert transcript.text == "Why these colours?"


def test_final_replacement_of_interim_does_not_duplicate_words():
    transcript = QuestionTranscript("fr")
    transcript.consume(result_payload("Qui a", final=False, duration=1))
    transcript.consume(result_payload("Qui a peint?", duration=2))
    transcript.consume(result_payload("Qui a", final=False, duration=1))
    assert transcript.text == "Qui a peint?"
    assert transcript.language == "fr"


@pytest.mark.parametrize(
    "question", ["", "uh", "Who painted", "Explain the", "Qui a peint", "Pourquoi euh"]
)
def test_obviously_incomplete_phrases_get_grace(question):
    assert question_needs_more_speech(question)


@pytest.mark.parametrize(
    "question",
    ["Who painted this?", "Why are the colours vivid?", "Qui a peint cette œuvre?"],
)
def test_complete_phrases_do_not_automatically_add_extra_wait(question):
    assert not question_needs_more_speech(question)


def test_cancel_propagates_through_cloud_and_local_adapters():
    primary, fallback = MockSTT(), MockSTT()
    calls = []
    primary.cancel_listen = lambda: calls.append("primary")
    fallback.cancel_listen = lambda: calls.append("fallback")
    FallbackSTT(primary, fallback).cancel_listen()
    assert calls == ["primary", "fallback"]


def test_private_transcript_is_not_logged_during_normal_capture(monkeypatch, caplog):
    capture(
        monkeypatch,
        [(0.5, True), (5, False)],
        payloads=[result_payload("synthetic private utterance", flush=True)],
    )
    assert "synthetic private utterance" not in caplog.text
