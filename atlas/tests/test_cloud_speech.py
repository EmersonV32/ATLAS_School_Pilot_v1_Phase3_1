"""Network-free tests for the cloud speech provider boundary."""

from __future__ import annotations

import base64
import io
import json
import logging
import queue
import sys
import threading
import types
from urllib.parse import parse_qs, urlparse

import numpy as np

from atlas.audio.cartesia_tts import (
    CartesiaTTS,
    build_cartesia_request,
    build_cartesia_url,
)
from atlas.audio.deepgram_stt import (
    DeepgramSTT,
    build_deepgram_url,
    parse_deepgram_result,
)
from atlas.audio.fallback import FallbackSTT, FallbackTTS
from atlas.audio.silero_vad import SileroVAD
from atlas.audio.stt import BaseSTT, TranscriptResult
from atlas.audio.tts import BaseTTS
from atlas.models.languages import ADMIN_LANGUAGE_OPTIONS


def test_deepgram_url_uses_nova_multilingual_privacy_and_keyterms():
    url = build_deepgram_url(
        model="nova-3",
        language="multi",
        sample_rate=16000,
        channels=1,
        endpointing_ms=400,
        keyterms=["Mona Lisa", "La Joconde"],
    )
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.scheme == "wss"
    assert parsed.netloc == "api.deepgram.com"
    assert query["model"] == ["nova-3"]
    assert query["language"] == ["multi"]
    assert query["mip_opt_out"] == ["true"]
    assert query["keyterm"] == ["Mona Lisa", "La Joconde"]
    assert "api_key" not in parsed.query.lower()
    assert "authorization" not in parsed.query.lower()


def test_deepgram_result_uses_detected_word_language():
    result = parse_deepgram_result(
        {
            "type": "Results",
            "is_final": True,
            "speech_final": True,
            "from_finalize": False,
            "channel": {
                "alternatives": [
                    {
                        "transcript": "Qui a peint la Joconde ?",
                        "confidence": 0.96,
                        "words": [{"word": "qui", "language": "fr-CA"}],
                    }
                ]
            },
        }
    )
    assert result is not None
    assert result.text == "Qui a peint la Joconde ?"
    assert result.language == "fr"
    assert result.confidence == 0.96
    assert result.is_final


def test_deepgram_result_uses_requested_language_when_metadata_is_absent():
    result = parse_deepgram_result(
        {
            "type": "Results",
            "is_final": True,
            "channel": {
                "alternatives": [
                    {
                        "transcript": "Qui a peint la Joconde ?",
                        "confidence": 0.99,
                        "words": [],
                    }
                ]
            },
        },
        default_language="fr",
    )
    assert result is not None
    assert result.language == "fr"


def test_deepgram_language_can_be_pinned_for_dashboard_session():
    stt = DeepgramSTT(language="multi", vad=object())
    for option in ADMIN_LANGUAGE_OPTIONS:
        stt.set_language(option.code)
        assert stt._language == option.code
    stt.set_language("zh-Hant")
    assert stt._language == "zh"
    stt.set_language("not-a-language")
    assert stt._language == "multi"


def test_deepgram_empty_final_is_noise_not_provider_failure(monkeypatch):
    class FakeVAD:
        threshold = 0.5

        def reset(self):
            self.calls = 0

        def probability(self, _pcm):
            self.calls += 1
            return 1.0 if self.calls == 1 else 0.0

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, samples):
            return (b"\x00\x00" * samples, False)

    class FakeConnection:
        def __init__(self):
            self.finalized = threading.Event()
            self.returned = False

        def send(self, payload):
            if isinstance(payload, str) and '"Finalize"' in payload:
                self.finalized.set()

        def recv(self):
            assert self.finalized.wait(timeout=1.0)
            if self.returned:
                return json.dumps({"type": "Metadata"})
            self.returned = True
            return json.dumps(
                {
                    "type": "Results",
                    "is_final": True,
                    "from_finalize": True,
                    "channel": {
                        "alternatives": [
                            {"transcript": "", "confidence": 0.0, "words": []}
                        ]
                    },
                }
            )

        def close(self):
            self.finalized.set()

    monkeypatch.setitem(
        sys.modules,
        "sounddevice",
        types.SimpleNamespace(RawInputStream=lambda **_kwargs: FakeStream()),
    )
    stt = DeepgramSTT(
        vad=FakeVAD(),
        min_speech_ms=0,
        min_silence_ms=0,
        final_timeout_s=0.5,
    )
    stt._ready = True
    stt._prepared_connection = FakeConnection()

    assert stt.listen(duration_s=0.5) is None


def test_deepgram_receiver_logs_deduplicated_live_transcripts(caplog):
    payloads = [
        {
            "type": "Results",
            "is_final": False,
            "channel": {
                "alternatives": [
                    {"transcript": "Peux-tu", "confidence": 0.8, "words": []}
                ]
            },
        },
        {
            "type": "Results",
            "is_final": False,
            "channel": {
                "alternatives": [
                    {"transcript": "Peux-tu", "confidence": 0.8, "words": []}
                ]
            },
        },
        {
            "type": "Results",
            "is_final": True,
            "channel": {
                "alternatives": [
                    {
                        "transcript": "Peux-tu me parler de la Mona Lisa?",
                        "confidence": 0.97,
                        "words": [],
                    }
                ]
            },
        },
        {"type": "Metadata"},
    ]

    class FakeConnection:
        def recv(self):
            return json.dumps(payloads.pop(0))

    messages = queue.Queue()
    caplog.set_level(logging.INFO, logger="atlas.audio.deepgram_stt")
    DeepgramSTT._receiver(
        FakeConnection(),
        messages,
        log_live_transcripts=True,
        default_language="fr",
    )

    assert caplog.text.count("[STT live] Peux-tu [") == 1
    assert "[STT live] Peux-tu me parler de la Mona Lisa?" in caplog.text
    assert messages.qsize() == 4


def test_cartesia_request_is_raw_pcm_and_language_normalized():
    request = build_cartesia_request(
        text="Bonjour.",
        language="fr-CA",
        model="sonic-3.5",
        voice_id="voice-id",
        sample_rate=24000,
        context_id="context-id",
    )
    assert build_cartesia_url("2026-03-01").startswith("wss://api.cartesia.ai/")
    assert request["model_id"] == "sonic-3.5"
    assert request["language"] == "fr"
    assert request["voice"] == {"mode": "id", "id": "voice-id"}
    assert request["output_format"] == {
        "container": "raw",
        "encoding": "pcm_s16le",
        "sample_rate": 24000,
    }


def test_cartesia_preserves_every_admin_language():
    for option in ADMIN_LANGUAGE_OPTIONS:
        request = build_cartesia_request(
            text="Museum test",
            language=option.code,
            model="sonic-3.5",
            voice_id="voice-id",
            sample_rate=24000,
            context_id=f"context-{option.code}",
        )
        assert request["language"] == option.code


def test_cartesia_records_first_audio_and_total_timing(monkeypatch):
    class FakeConnection:
        def __init__(self):
            self.context_id = ""
            self.messages: list[dict[str, object]] = []

        def send(self, raw: str) -> None:
            self.context_id = json.loads(raw)["context_id"]
            self.messages = [
                {
                    "type": "chunk",
                    "context_id": self.context_id,
                    "data": base64.b64encode(b"\x00\x00").decode(),
                },
                {"type": "done", "context_id": self.context_id},
            ]

        def recv(self, timeout: float) -> str:
            assert timeout == 15.0
            return json.dumps(self.messages.pop(0))

    class FakePlayer:
        def __init__(self):
            self.stdin = io.BytesIO()

    player = FakePlayer()
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.open_raw_player",
        lambda *_args, **_kwargs: player,
    )
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.finish_raw_player",
        lambda *_args, **_kwargs: True,
    )

    tts = CartesiaTTS(voice_id="voice-id")
    tts._connection = FakeConnection()
    assert tts.speak("Bonjour", language="fr")
    assert player.stdin.getvalue() == b"\x00\x00"
    assert tts.last_first_audio_ms is not None
    assert tts.last_first_audio_ms >= 0
    assert tts.last_total_ms is not None
    assert tts.last_total_ms >= tts.last_first_audio_ms


def test_cartesia_continuous_utterance_reuses_one_context(monkeypatch):
    class FakeConnection:
        def __init__(self):
            self.requests: list[dict[str, object]] = []
            self.messages: queue.Queue[dict[str, object]] = queue.Queue()

        def send(self, raw: str) -> None:
            request = json.loads(raw)
            self.requests.append(request)
            if len(self.requests) == 1:
                self.messages.put(
                    {
                        "type": "chunk",
                        "context_id": request["context_id"],
                        "data": base64.b64encode(b"\x01\x02").decode(),
                    }
                )
            if request["continue"] is False:
                self.messages.put(
                    {"type": "done", "context_id": request["context_id"]}
                )

        def recv(self, timeout: float) -> str:
            return json.dumps(self.messages.get(timeout=timeout))

    class FakePlayer:
        def __init__(self):
            self.stdin = io.BytesIO()

        def poll(self):
            return None

    player = FakePlayer()
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.open_raw_player", lambda *_args: player
    )
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.finish_raw_player",
        lambda *_args, **_kwargs: True,
    )
    connection = FakeConnection()
    tts = CartesiaTTS(voice_id="voice-id")
    tts._connection = connection

    assert tts.begin_utterance("en")
    assert tts.speak_segment("First sentence.", "en")
    assert tts.speak_segment("Second sentence.", "en")
    assert tts.end_utterance()

    assert [request["continue"] for request in connection.requests] == [
        True,
        True,
        False,
    ]
    assert connection.requests[-1]["transcript"] == ""
    assert len({request["context_id"] for request in connection.requests}) == 1
    assert player.stdin.getvalue() == b"\x01\x02"
    assert tts.last_first_audio_ms is not None


def test_fallback_tts_keeps_primary_for_continuous_utterance():
    class StreamingTTS(_FakeTTS):
        def __init__(self):
            super().__init__(True)
            self.segments: list[str] = []

        def begin_utterance(self, language="en"):
            return True

        def speak_segment(self, text, language="en"):
            self.segments.append(text)
            return True

        def end_utterance(self):
            return True

    primary = StreamingTTS()
    fallback = _FakeTTS(True)
    tts = FallbackTTS(primary, fallback)
    tts.warm_up()

    assert tts.begin_utterance("en")
    assert tts.speak_segment("First sentence.", "en")
    assert tts.speak_segment("Second sentence.", "en")
    assert tts.end_utterance()
    assert primary.segments == ["First sentence.", "Second sentence."]
    assert fallback.spoken == []
    assert tts.last_provider == "StreamingTTS"


def test_cartesia_reconnects_once_when_warm_socket_is_stale(monkeypatch):
    class StaleConnection:
        def __init__(self):
            self.closed = False

        def send(self, _raw: str) -> None:
            raise RuntimeError("connection idle timeout")

        def close(self) -> None:
            self.closed = True

    class FreshConnection:
        def __init__(self):
            self.context_id = ""
            self.messages = []

        def send(self, raw: str) -> None:
            self.context_id = json.loads(raw)["context_id"]
            self.messages = [
                {
                    "type": "chunk",
                    "context_id": self.context_id,
                    "data": base64.b64encode(b"\x00\x00").decode(),
                },
                {"type": "done", "context_id": self.context_id},
            ]

        def recv(self, timeout: float) -> str:
            assert timeout == 15.0
            return json.dumps(self.messages.pop(0))

        def close(self) -> None:
            return None

    class FakePlayer:
        def __init__(self):
            self.stdin = io.BytesIO()

    player = FakePlayer()
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.open_raw_player", lambda *_args: player
    )
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.finish_raw_player",
        lambda *_args, **_kwargs: True,
    )
    stale = StaleConnection()
    fresh = FreshConnection()
    tts = CartesiaTTS(voice_id="voice-id")
    tts._connection = stale
    tts._connect = lambda: fresh

    assert tts.speak("Bonjour", language="fr")
    assert stale.closed
    assert player.stdin.getvalue() == b"\x00\x00"


def test_silero_onnx_wrapper_carries_recurrent_state_without_torch():
    class FakeSession:
        def __init__(self):
            self.calls = []

        def run(self, _outputs, inputs):
            self.calls.append(inputs)
            return np.array([[0.75]], dtype=np.float32), inputs["state"] + 1

    session = FakeSession()
    vad = SileroVAD(session=session)
    vad.warm_up()
    probability = vad.probability(np.zeros(512, dtype="<i2").tobytes())
    assert probability == 0.75
    assert session.calls[0]["input"].shape == (1, 576)
    assert session.calls[0]["state"].shape == (2, 1, 128)


class _FakeSTT(BaseSTT):
    def __init__(self, *, error: bool = False, text: str = "fallback") -> None:
        self.error = error
        self.text = text
        self.warmed = False

    def warm_up(self) -> None:
        self.warmed = True

    def listen(self, duration_s: float = 5.0) -> TranscriptResult | None:
        if self.error:
            raise RuntimeError("provider failed")
        return TranscriptResult(text=self.text)


class _FakeTTS(BaseTTS):
    def __init__(self, result: bool) -> None:
        self.result = result
        self.spoken: list[str] = []
        self.playback_started = False

    def warm_up(self) -> None:
        return None

    def speak(self, text: str, language: str = "en") -> bool:
        self.spoken.append(text)
        return self.result


def test_stt_failure_switches_next_question_to_local_fallback(caplog):
    caplog.set_level(logging.INFO, logger="atlas.audio.fallback")
    primary = _FakeSTT(error=True)
    fallback = _FakeSTT(text="local answer")
    stt = FallbackSTT(primary, fallback)
    stt.warm_up()
    assert stt.listen() is None
    result = stt.listen()
    assert result is not None
    assert result.text == "local answer"
    assert stt.last_provider == "_FakeSTT"
    assert "primary" in stt.provider_status()
    assert "Primary _FakeSTT failed" in caplog.text


def test_stt_no_transcript_keeps_cloud_primary_ready():
    class SilentPrimary(_FakeSTT):
        def listen(self, duration_s=5.0):
            return None

    primary = SilentPrimary()
    fallback = _FakeSTT(text="must not be used")
    stt = FallbackSTT(primary, fallback)
    stt.warm_up()

    assert stt.listen() is None
    assert stt.primary_ready
    assert stt.last_provider == "SilentPrimary"


def test_stt_failure_recovers_current_question_from_captured_pcm():
    class PrimaryWithPCM(_FakeSTT):
        last_audio_pcm = b"\x00\x01" * 32

    class FallbackWithPCM(_FakeSTT):
        def transcribe_pcm(self, pcm):
            assert pcm == PrimaryWithPCM.last_audio_pcm
            return TranscriptResult(text="recovered question", language="fr")

    stt = FallbackSTT(PrimaryWithPCM(error=True), FallbackWithPCM())
    stt.warm_up()
    result = stt.listen()

    assert result is not None
    assert result.text == "recovered question"


def test_stt_primary_retries_after_transient_failure():
    class TransientPrimary(_FakeSTT):
        def __init__(self):
            super().__init__(text="cloud answer")
            self.listen_calls = 0

        def listen(self, duration_s=5.0):
            self.listen_calls += 1
            if self.listen_calls == 1:
                raise RuntimeError("temporary Deepgram failure")
            return super().listen(duration_s)

    primary = TransientPrimary()
    stt = FallbackSTT(
        primary,
        _FakeSTT(text="local answer"),
        primary_retry_interval_s=0,
    )
    stt.warm_up()

    assert stt.listen() is None
    stt.prepare_listen()
    recovered = stt.listen()

    assert recovered is not None
    assert recovered.text == "cloud answer"
    assert stt.primary_ready


def test_tts_falls_back_before_any_cloud_audio_started(caplog):
    caplog.set_level(logging.INFO, logger="atlas.audio.fallback")
    primary = _FakeTTS(False)
    fallback = _FakeTTS(True)
    tts = FallbackTTS(primary, fallback)
    tts.warm_up()
    assert tts.speak("Museum answer")
    assert primary.spoken == ["Museum answer"]
    assert fallback.spoken == ["Museum answer"]
    assert tts.last_provider == "_FakeTTS"
    assert "fallback" in tts.provider_status()
    assert "produced no audio; switching" in caplog.text
