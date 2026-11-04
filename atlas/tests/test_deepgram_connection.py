"""Synthetic sockets and PCM: exercise persistent STT across real turn boundaries."""

from __future__ import annotations

import copy
import json
import queue
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from atlas.audio import deepgram_stt
from atlas.audio.deepgram_connection import (
    ReusableDeepgramConnection,
    payload_for_turn,
)
from atlas.audio.deepgram_stt import DeepgramError, DeepgramSTT


def results(text, start, duration, *, flushed=True, words=None):
    return {
        "type": "Results",
        "start": start,
        "duration": duration,
        "is_final": True,
        "from_finalize": flushed,
        "channel": {"alternatives": [{
            "transcript": text,
            "confidence": 0.9,
            "words": words or [],
        }]},
    }


class Socket:
    """A streaming provider whose result timestamps accumulate across turns."""

    def __init__(self, answers):
        self.answers = iter(answers)
        self.incoming = queue.Queue()
        self.sent = []
        self.total_bytes = 0
        self.turn_start = None
        self.closed = False
        self.final_payloads = []
        self.keepalive_seen = threading.Event()
        self.fail_keepalive = False
        self.confirm_flush = True
        self.flush_text_override = None

    @property
    def audio_seconds(self):
        return self.total_bytes / 32000

    def send(self, payload):
        if self.closed:
            raise OSError("Synthetic socket closed")
        if isinstance(payload, bytes):
            if any(payload) and self.turn_start is None:
                self.turn_start = self.audio_seconds
            self.total_bytes += len(payload)
        else:
            kind = json.loads(payload)["type"]
            if kind == "KeepAlive":
                self.keepalive_seen.set()
                if self.fail_keepalive:
                    raise OSError("Synthetic keepalive failure")
            elif kind == "Finalize":
                text = next(self.answers)
                if self.flush_text_override is not None:
                    text = self.flush_text_override
                start = self.turn_start
                assert start is not None
                reply = results(
                    text, start, self.audio_seconds - start,
                    flushed=self.confirm_flush,
                )
                self.final_payloads.append(reply)
                self.incoming.put(json.dumps(reply))
                self.turn_start = None
        self.sent.append(payload)

    def recv(self):
        return self.incoming.get(timeout=2)

    def close(self):
        if not self.closed:
            self.closed = True
            self.incoming.put(None)


@pytest.mark.parametrize("sample_rate,channels", [(16000, 1), (22050, 1), (44100, 2)])
def test_initial_silence_contains_complete_pcm_frames(sample_rate, channels):
    socket = Socket([])
    stream = ReusableDeepgramConnection(
        socket, DeepgramSTT._receiver, sample_rate=sample_rate, channels=channels,
    )
    try:
        stream.start()
        seed = socket.sent[0]
        assert isinstance(seed, bytes) and not any(seed)
        assert len(seed) % (channels * 2) == 0
        assert 0 < stream.audio_seconds <= 0.01
        assert stream.audio_seconds == len(seed) / (sample_rate * channels * 2)
    finally:
        stream.close()


@pytest.fixture
def capture_harness(monkeypatch):
    state = SimpleNamespace(
        opened=0, reads=0, input_open=False, cancel_at=None,
        on_open=None, on_read=None, voices=16, adapter=None, turn_offset=0,
    )
    real_started = time.monotonic()
    clock = SimpleNamespace(audio_elapsed=0.0)

    def monotonic():
        # Capture advances by deterministic audio frames. Real elapsed time also
        # advances flush deadlines when a provider intentionally omits its ACK.
        return clock.audio_elapsed + time.monotonic() - real_started

    class VAD:
        threshold = 0.5

        def reset(self):
            state.reads = 0

        def probability(self, _pcm):
            return float(state.reads <= state.voices)

    class Input:
        def __enter__(self):
            state.opened += 1
            state.input_open = True
            state.turn_offset = state.adapter._stream.audio_seconds
            if state.on_open is not None:
                state.on_open()
            return self

        def __exit__(self, *_args):
            state.input_open = False

        def read(self, samples):
            state.reads += 1
            clock.audio_elapsed += samples / 16000
            if state.on_read is not None:
                state.on_read()
            if state.reads == state.cancel_at:
                state.adapter.cancel_listen()
            return b"\x01\x00" * samples, False

    sockets = []

    def connect():
        socket = Socket(["Who painted the Mona Lisa?", "When was it made?"])
        sockets.append(socket)
        return socket

    def transport(*args, **kwargs):
        return ReusableDeepgramConnection(*args, keepalive_s=0.01, **kwargs)

    adapter = DeepgramSTT(
        vad=VAD(), min_silence_ms=1000, hesitation_silence_ms=2000,
        final_timeout_s=0.02,
    )
    state.adapter = adapter
    adapter._ready = True
    monkeypatch.setattr(adapter, "_connect", connect)
    monkeypatch.setattr(deepgram_stt, "ReusableDeepgramConnection", transport)
    monkeypatch.setattr(
        deepgram_stt, "time",
        SimpleNamespace(monotonic=monotonic, perf_counter=monotonic),
    )
    monkeypatch.setitem(
        sys.modules, "sounddevice",
        SimpleNamespace(RawInputStream=lambda **_kwargs: Input()),
    )
    try:
        yield SimpleNamespace(adapter=adapter, sockets=sockets, state=state)
    finally:
        adapter.close()
        for socket in sockets:
            socket.close()


def test_two_questions_reuse_socket_without_repeating_old_transcript(capture_harness):
    rig = capture_harness
    rig.adapter.prepare_listen()
    first = rig.adapter.listen()
    assert first.text == "Who painted the Mona Lisa?"
    assert len(rig.sockets) == 1
    old = rig.sockets[0].final_payloads[0]
    rig.state.on_open = lambda: rig.sockets[0].incoming.put(json.dumps(old))
    rig.adapter.prepare_listen()
    second = rig.adapter.listen()
    assert second.text == "When was it made?"
    assert len(rig.sockets) == 1
    assert not rig.sockets[0].closed
    assert rig.state.opened == 2


def test_idle_response_period_uses_keepalive_without_capturing_audio(capture_harness):
    rig = capture_harness
    rig.adapter.prepare_listen()
    assert rig.adapter.listen().text == "Who painted the Mona Lisa?"
    socket = rig.sockets[0]
    audio_before = [x for x in socket.sent if isinstance(x, bytes)]
    opened_before = rig.state.opened
    offset_before = rig.adapter._stream.audio_seconds
    socket.keepalive_seen.clear()
    assert socket.keepalive_seen.wait(1)
    assert not rig.state.input_open
    assert rig.state.opened == opened_before
    assert [x for x in socket.sent if isinstance(x, bytes)] == audio_before
    assert rig.adapter._stream.audio_seconds == offset_before


def test_reused_socket_preserves_short_prepared_question_endpoint(capture_harness):
    rig = capture_harness
    rig.adapter.prepare_listen()
    assert rig.adapter.listen().text == "Who painted the Mona Lisa?"
    assert rig.adapter._stream.audio_seconds > 1
    rig.sockets[0].flush_text_override = ""

    def deliver_complete_final():
        if rig.state.reads == 17:
            rig.adapter._stream.messages.put_nowait(results(
                "Who painted the Mona Lisa?", rig.state.turn_offset, 16 * 0.032,
                flushed=False,
            ))

    rig.state.on_read = deliver_complete_final
    rig.adapter.prepare_listen()
    answer = rig.adapter.listen()
    assert answer.text == "Who painted the Mona Lisa?"
    assert 0.3 <= (
        answer.transcript_ready_monotonic_s - answer.speech_end_monotonic_s
    ) < 0.38
    assert len(rig.sockets) == 1
    finalizes = [
        x for x in rig.sockets[0].sent
        if isinstance(x, str) and json.loads(x)["type"] == "Finalize"
    ]
    assert len(finalizes) == 1  # First turn flushed; the complete second final did not.


def test_timed_final_prefix_cannot_skip_flush_for_later_speech(capture_harness):
    rig = capture_harness
    rig.adapter.prepare_listen()
    socket = rig.sockets[0]
    socket.confirm_flush = False
    socket.flush_text_override = "the Mona Lisa?"

    def deliver_prefix():
        if rig.state.reads == 12:
            rig.adapter._stream.messages.put_nowait(results(
                "Who painted", rig.state.turn_offset, 12 * 0.032, flushed=False,
            ))

    rig.state.on_read = deliver_prefix
    answer = rig.adapter.listen()
    assert answer.text == "Who painted the Mona Lisa?"
    assert any(
        isinstance(x, str) and json.loads(x)["type"] == "Finalize"
        for x in socket.sent
    )
    assert socket.closed  # No ACK: never carry this stream into another turn.
    assert rig.adapter._stream is None


def test_quiet_listening_window_does_not_close_the_ready_connection(capture_harness):
    rig = capture_harness
    rig.state.voices = 0
    rig.adapter.prepare_listen()
    assert rig.adapter.listen(duration_s=0.15) is None
    assert not rig.sockets[0].closed
    assert len(rig.sockets) == 1
    # Initial generated silence is the only binary message without visitor speech.
    assert all(not any(x) for x in rig.sockets[0].sent if isinstance(x, bytes))
    rig.adapter.prepare_listen()
    assert len(rig.sockets) == 1


def test_language_change_retires_old_socket_and_prepares_a_new_one(capture_harness):
    rig = capture_harness
    rig.adapter.prepare_listen()
    old = rig.sockets[0]
    rig.adapter.set_language("fr")
    assert old.closed
    assert rig.adapter._stream is None
    rig.adapter.prepare_listen()
    assert len(rig.sockets) == 2
    assert rig.adapter._language == "fr"


def test_preparing_during_language_change_cannot_keep_the_old_language(
    capture_harness, monkeypatch,
):
    rig = capture_harness
    rig.adapter.prepare_listen()
    old = rig.sockets[0]
    original_close = old.close
    closing, release = threading.Event(), threading.Event()
    errors = []

    def delayed_close():
        closing.set()
        assert release.wait(1)
        original_close()

    def connect_with_language():
        socket = Socket([])
        socket.prepared_language = rig.adapter._language
        rig.sockets.append(socket)
        return socket

    def change_language():
        try:
            rig.adapter.set_language("fr")
        except Exception as exc:
            errors.append(exc)

    monkeypatch.setattr(old, "close", delayed_close)
    monkeypatch.setattr(rig.adapter, "_connect", connect_with_language)
    worker = threading.Thread(target=change_language)
    worker.start()
    try:
        assert closing.wait(1)
        try:
            rig.adapter.prepare_listen()
        except DeepgramError:
            pass  # Rejecting a preparation across a language boundary is safe.
    finally:
        release.set()
        worker.join(timeout=2)
    assert not worker.is_alive()
    assert not errors
    rig.adapter.prepare_listen()
    assert rig.adapter._stream.connection.prepared_language == "fr"


def test_cancelled_capture_discards_old_audio_and_does_not_finalize(capture_harness):
    rig = capture_harness
    rig.state.cancel_at = 3
    rig.adapter.prepare_listen()
    assert rig.adapter.listen() is None
    assert rig.adapter.last_audio_pcm == b""
    assert rig.sockets[0].closed
    assert not any(
        isinstance(x, str) and json.loads(x)["type"] == "Finalize"
        for x in rig.sockets[0].sent
    )


def test_server_eof_is_replaced_before_the_next_microphone_opens(capture_harness):
    rig = capture_harness
    rig.adapter.prepare_listen()
    old = rig.adapter._stream
    rig.sockets[0].incoming.put(None)
    assert old._ended.wait(1)
    rig.adapter.prepare_listen()
    assert len(rig.sockets) == 2
    assert rig.sockets[0].closed
    assert rig.state.opened == 0


def test_failed_keepalive_is_reconnected_before_next_capture(capture_harness):
    rig = capture_harness
    rig.adapter.prepare_listen()
    old = rig.adapter._stream
    socket = rig.sockets[0]
    socket.fail_keepalive = True
    assert old._stop.wait(1)
    rig.adapter.prepare_listen()
    assert len(rig.sockets) == 2
    assert socket.closed
    assert rig.state.opened == 0


def test_flush_timeout_returns_available_text_but_never_reuses_unflushed_socket(
    capture_harness,
):
    rig = capture_harness
    rig.adapter.prepare_listen()
    socket = rig.sockets[0]
    socket.confirm_flush = False
    answer = rig.adapter.listen()
    assert answer.text == "Who painted the Mona Lisa?"
    assert socket.closed
    assert rig.adapter._stream is None
    rig.adapter.prepare_listen()
    assert len(rig.sockets) == 2


def test_cancel_during_connection_setup_cannot_leave_a_ready_stale_socket(
    capture_harness, monkeypatch,
):
    rig = capture_harness
    entered, release = threading.Event(), threading.Event()
    socket = Socket([])
    rig.sockets.append(socket)
    errors = []

    def delayed_connect():
        entered.set()
        assert release.wait(1)
        return socket

    def prepare():
        try:
            rig.adapter.prepare_listen()
        except DeepgramError as exc:
            errors.append(exc)

    monkeypatch.setattr(rig.adapter, "_connect", delayed_connect)
    worker = threading.Thread(target=prepare)
    worker.start()
    assert entered.wait(1)
    rig.adapter.cancel_listen()
    release.set()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert len(errors) == 1
    assert socket.closed
    assert rig.adapter._stream is None
    assert rig.state.opened == 0


def test_normalization_excludes_old_words_from_a_straddling_result():
    payload = results("Old. New?", 9.0, 3.0, words=[
        {"word": "old", "punctuated_word": "Old.", "start": 9.1, "end": 9.8},
        {"word": "new", "punctuated_word": "New?", "start": 10.2, "end": 11.0},
    ])
    original = copy.deepcopy(payload)
    current = payload_for_turn(payload, 10.0)
    alternative = current["channel"]["alternatives"][0]
    assert alternative["transcript"] == "New?"
    assert alternative["words"][0]["start"] == pytest.approx(0.2)
    assert alternative["words"][0]["end"] == 1.0
    assert current["start"] == 0.0
    assert current["duration"] == 2.0
    assert payload == original


@pytest.mark.parametrize("flushed", [False, True])
def test_previous_turn_result_including_late_flush_is_not_current(flushed):
    assert payload_for_turn(results("Old answer", 0, 10, flushed=flushed), 10) is None


@pytest.mark.parametrize(
    "timing",
    [{}, {"start": 0}, {"start": float("nan"), "duration": 1},
     {"start": 1, "duration": float("inf")}, {"start": 2, "duration": -1}],
)
def test_missing_or_invalid_timing_cannot_cross_a_turn_boundary(timing):
    payload = results("Untrusted boundary", 0, 1)
    payload.pop("start")
    payload.pop("duration")
    payload.update(timing)
    assert payload_for_turn(payload, 0) is None


def test_straddling_text_without_word_boundaries_is_not_guessed():
    assert payload_for_turn(results("May include prior words", 9, 3), 10) is None
