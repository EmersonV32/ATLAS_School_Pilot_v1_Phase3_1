"""Visit cancellation: synthetic sockets/processes, no audio or credentials."""
import io
import json
import threading
from types import SimpleNamespace

from atlas.audio.cartesia_tts import CartesiaTTS
from atlas.audio.fallback import FallbackTTS
from atlas.audio.piper_tts import PiperTTS
from atlas.audio.tts import BaseTTS


def test_whole_answer_socket_is_cancelled_without_waiting_for_speech():
    entered, released = threading.Event(), threading.Event()

    class Connection:
        def send(self, _request):
            pass

        def recv(self, **_kwargs):
            entered.set()
            assert released.wait(3)
            raise OSError("Synthetic socket closed")

        def close(self):
            released.set()

    tts = CartesiaTTS(voice_id="synthetic-voice")
    tts._connection = Connection()
    connects = []
    tts._connect = lambda: connects.append(True) or Connection()
    results = []
    speaking = threading.Thread(target=lambda: results.append(tts.speak("Old visit")))
    speaking.start()
    assert entered.wait(1)
    aborting = threading.Thread(target=tts.abort_utterance)
    aborting.start()
    try:
        aborting.join(0.5)
        assert not aborting.is_alive(), "Cancellation must not wait for the speech lock"
    finally:
        released.set()
        speaking.join(2)
        aborting.join(2)
    assert results == [False]
    assert not connects, "Cancellation before first audio must not retry the old answer"


def test_cancelled_primary_does_not_replay_the_old_answer_with_fallback():
    entered, released = threading.Event(), threading.Event()

    class Provider(BaseTTS):
        playback_started = False

        def __init__(self, primary=False):
            self.primary = primary
            self.spoken = []
            self.aborts = 0

        def speak(self, text, language="en"):
            self.spoken.append(text)
            if self.primary:
                entered.set()
                assert released.wait(3)
                return False
            return True

        def abort_utterance(self):
            self.aborts += 1
            released.set()

    primary, fallback = Provider(True), Provider()
    tts = FallbackTTS(primary, fallback)
    tts.warm_up()
    results = []
    speaking = threading.Thread(target=lambda: results.append(tts.speak("Old visit")))
    speaking.start()
    assert entered.wait(1)
    tts.abort_utterance()
    speaking.join(2)
    assert not speaking.is_alive()
    assert results == [False]
    assert fallback.aborts == 1
    assert not fallback.spoken


def test_piper_cancellation_kills_only_its_owned_playback(monkeypatch, tmp_path):
    entered, released = threading.Event(), threading.Event()
    player = SimpleNamespace(returncode=None, killed=False)

    def communicate(**_kwargs):
        entered.set()
        assert released.wait(3)
        player.returncode = -9 if player.killed else 0
        return b"", b""

    def kill():
        player.killed = True
        released.set()

    player.communicate = communicate
    player.kill = kill
    player.poll = lambda: player.returncode
    monkeypatch.setattr(
        "atlas.audio.piper_tts.subprocess.Popen", lambda *_a, **_k: player,
    )
    # Old implementation must also remain synthetic during the failing repro.
    monkeypatch.setattr(
        "atlas.audio.piper_tts.subprocess.run",
        lambda *_a, **_k: communicate() and SimpleNamespace(returncode=0, stderr=b""),
    )
    monkeypatch.setattr("atlas.audio.piper_tts.find_pulse_playback", lambda _n: None)
    monkeypatch.setattr("atlas.audio.piper_tts.find_alsa_playback", lambda _n: "mock")
    wav = tmp_path / "synthetic.wav"
    wav.write_bytes(b"synthetic placeholder")
    tts = PiperTTS("mock-en", "mock-fr")
    results = []
    speaking = threading.Thread(target=lambda: results.append(tts._play_wav(str(wav))))
    speaking.start()
    assert entered.wait(1)
    try:
        tts.abort_utterance()
        assert player.killed
    finally:
        released.set()
        speaking.join(2)
    assert results == [False]


def test_cartesia_cancellation_kills_player_after_first_audio(monkeypatch):
    import base64

    entered, released = threading.Event(), threading.Event()
    player = SimpleNamespace(stdin=io.BytesIO(), killed=False)
    player.poll = lambda: -9 if player.killed else None
    player.kill = lambda: (setattr(player, "killed", True), released.set())

    class Connection:
        def send(self, raw):
            self.context_id = json.loads(raw)["context_id"]
            self.first = True

        def recv(self, **_kwargs):
            if self.first:
                self.first = False
                return json.dumps({"type": "chunk", "context_id": self.context_id,
                                   "data": base64.b64encode(b"\x00\x00").decode()})
            entered.set()
            assert released.wait(3)
            raise OSError("Synthetic cancellation")

        def close(self):
            released.set()

    monkeypatch.setattr("atlas.audio.cartesia_tts.open_raw_player", lambda *_a: player)
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.finish_raw_player", lambda *_a, **_k: False,
    )
    tts = CartesiaTTS(voice_id="synthetic-voice")
    tts._connection = Connection()
    speaking = threading.Thread(target=lambda: tts.speak("Old answer"))
    speaking.start()
    assert entered.wait(1)
    aborting = threading.Thread(target=tts.abort_utterance)
    aborting.start()
    try:
        aborting.join(0.5)
        assert player.killed
    finally:
        released.set()
        speaking.join(2)
        aborting.join(2)


def test_cartesia_cancel_during_player_start_discards_late_stream_chunk(monkeypatch):
    import base64

    entered, released = threading.Event(), threading.Event()
    player = SimpleNamespace(stdin=io.BytesIO(), killed=False)
    player.poll = lambda: -9 if player.killed else None
    player.kill = lambda: setattr(player, "killed", True)

    class Connection:
        def recv(self, **_kwargs):
            return json.dumps({"type": "chunk", "context_id": "old-context",
                               "data": base64.b64encode(b"\x00\x00").decode()})

        def close(self):
            released.set()

    def open_player(*_args):
        entered.set()
        assert released.wait(3)
        return player

    monkeypatch.setattr("atlas.audio.cartesia_tts.open_raw_player", open_player)
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.finish_raw_player", lambda *_a, **_k: False,
    )
    tts = CartesiaTTS(voice_id="synthetic-voice")
    tts._connection = Connection()
    tts._utterance_context_id = "old-context"
    worker = threading.Thread(target=tts._receive_utterance, args=("old-context",))
    tts._utterance_thread = worker
    worker.start()
    assert entered.wait(1)
    try:
        tts.abort_utterance()
    finally:
        released.set()
        worker.join(2)
    assert not worker.is_alive()
    assert player.killed, "A player created after cancellation must also be killed"
    assert player.stdin.getvalue() == b"", "No cancelled chunk may enter playback"


def test_cartesia_cancel_during_connect_does_not_start_late_answer():
    entered, released = threading.Event(), threading.Event()
    sent = []
    connection = SimpleNamespace(send=sent.append, close=lambda: None)

    def connect():
        entered.set()
        assert released.wait(3)
        return connection

    tts = CartesiaTTS(voice_id="synthetic-voice")
    tts._connect = connect
    results = []
    worker = threading.Thread(target=lambda: results.append(tts.speak("Old visit")))
    worker.start()
    assert entered.wait(1)
    try:
        tts.abort_utterance()
    finally:
        released.set()
        worker.join(2)
    assert results == [False]
    assert not sent
    assert tts._connection is None
