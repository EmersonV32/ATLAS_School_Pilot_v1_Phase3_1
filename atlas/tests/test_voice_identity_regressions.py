"""Synthetic voice identity guards; no provider, audio hardware, or credentials."""

from __future__ import annotations

import base64
import io
import json
import threading

import pytest

from atlas.audio.cartesia_tts import CartesiaTTS
from atlas.audio.fallback import FallbackTTS
from atlas.audio.tts import BaseTTS
from atlas.models.languages import ADMIN_LANGUAGE_OPTIONS

LANGUAGES = [option.code for option in ADMIN_LANGUAGE_OPTIONS]
PCM_CHUNKS = [bytes((index, 0)) * 64 for index in range(1, 9)]


class FakePlayer:
    def __init__(self):
        self.stdin = io.BytesIO()
        self.killed = False

    def poll(self):
        return -9 if self.killed else None

    def kill(self):
        self.killed = True


class FakeSocket:
    def __init__(self, *, late_error=False, stale_context=None):
        self.requests = []
        self.messages = []
        self.closed = False
        self.late_error = late_error
        self.stale_context = stale_context or "unrelated-old-answer"

    def send(self, raw):
        request = json.loads(raw)
        self.requests.append(request)
        context = request["context_id"]
        # Leftover chunks, errors, and completion must not affect this answer.
        self.messages.extend(
            [
                {"type": "chunk", "context_id": self.stale_context,
                 "data": base64.b64encode(b"\x7f\x7f").decode()},
                {"type": "error", "context_id": self.stale_context,
                 "message": "Synthetic stale error"},
                {"type": "done", "context_id": self.stale_context},
            ]
        )
        self.messages.extend(
            {"type": "chunk", "context_id": context,
             "data": base64.b64encode(chunk).decode()}
            for chunk in PCM_CHUNKS
        )
        self.messages.append(
            {"type": "error", "context_id": context,
             "message": "Synthetic late provider failure"}
            if self.late_error else {"type": "done", "context_id": context}
        )

    def recv(self, **_kwargs):
        assert self.messages, "Unexpected receive after answer completion"
        return json.dumps(self.messages.pop(0))

    def close(self):
        self.closed = True


@pytest.fixture
def players(monkeypatch):
    opened = []

    def open_player(*_args):
        player = FakePlayer()
        opened.append(player)
        return player

    monkeypatch.setattr("atlas.audio.cartesia_tts.open_raw_player", open_player)
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.finish_raw_player",
        lambda player, **_kwargs: not player.killed,
    )
    return opened


@pytest.mark.parametrize("language", LANGUAGES)
def test_whole_answer_uses_one_identity_context_and_player(language, players):
    socket = FakeSocket()
    tts = CartesiaTTS(voice_id="synthetic-fixed-voice")
    tts._connection = socket
    connects = []
    tts._connect = lambda: connects.append(True) or FakeSocket()

    assert tts.speak(
        "Synthetic first sentence. Synthetic follow-up sentence.", language
    )

    assert not connects
    assert len(socket.requests) == 1
    request = socket.requests[0]
    assert request["voice"] == {"mode": "id", "id": "synthetic-fixed-voice"}
    assert request["language"] == language
    assert request["continue"] is False
    assert request["context_id"] != socket.stale_context
    assert len(players) == 1
    assert players[0].stdin.getvalue() == b"".join(PCM_CHUNKS)
    assert not socket.messages


class FakeFallback(BaseTTS):
    def __init__(self):
        self.spoken = []

    def speak(self, text, language="en"):
        self.spoken.append((text, language))
        return True


@pytest.mark.parametrize("language", LANGUAGES)
def test_late_stream_failure_never_retries_or_switches_voice(language, players):
    socket = FakeSocket(late_error=True)
    primary = CartesiaTTS(voice_id="synthetic-fixed-voice")
    primary._connection = socket
    connects = []
    primary._connect = lambda: connects.append(True) or FakeSocket()
    fallback = FakeFallback()
    tts = FallbackTTS(primary, fallback)
    tts.primary_ready = tts.fallback_ready = True

    assert not tts.speak("Synthetic answer with a late network failure.", language)

    assert primary.playback_started
    assert not connects, "Already audible answers must never be restarted"
    assert len(socket.requests) == 1
    assert len(players) == 1
    assert players[0].stdin.getvalue() == b"".join(PCM_CHUNKS)
    assert not fallback.spoken, "A late failure must never switch to a new voice"


@pytest.mark.parametrize("language", LANGUAGES)
def test_cancelled_context_cannot_contaminate_the_next_answer(language, players):
    entered, released = threading.Event(), threading.Event()

    class CancelledSocket:
        context = None

        def send(self, raw):
            self.context = json.loads(raw)["context_id"]

        def recv(self, **_kwargs):
            entered.set()
            assert released.wait(3), "Synthetic cancellation did not release receive"
            return json.dumps(
                {"type": "chunk", "context_id": self.context,
                 "data": base64.b64encode(b"\x7f\x7f").decode()}
            )

        def close(self):
            released.set()

    old = CancelledSocket()
    tts = CartesiaTTS(voice_id="synthetic-fixed-voice")
    tts._connection = old
    results = []
    worker = threading.Thread(
        target=lambda: results.append(tts.speak("Cancelled old answer", language))
    )
    worker.start()
    assert entered.wait(1)
    try:
        tts.abort_utterance()
    finally:
        released.set()
        worker.join(3)
    assert not worker.is_alive()
    assert results == [False]
    assert not players, "No late cancelled chunk may create a playback process"

    fresh = FakeSocket(stale_context=old.context)
    tts._connection = fresh
    assert tts.speak("Only this new answer may be heard.", language)
    assert fresh.requests[0]["context_id"] != old.context
    assert len(players) == 1
    assert players[0].stdin.getvalue() == b"".join(PCM_CHUNKS)
