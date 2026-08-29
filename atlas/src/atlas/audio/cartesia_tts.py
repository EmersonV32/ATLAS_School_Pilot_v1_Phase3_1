"""Cartesia Sonic 3.5 streaming TTS for the Shokz USB headset."""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
import uuid
from typing import Any
from urllib.parse import urlencode

from .playback import (
    finish_raw_player,
    listening_cue_pcm,
    open_raw_player,
    play_pcm,
)
from .tts import BaseTTS

logger = logging.getLogger(__name__)


def build_cartesia_url(api_version: str) -> str:
    return "wss://api.cartesia.ai/tts/websocket?" + urlencode(
        {"cartesia_version": api_version}
    )


def build_cartesia_request(
    *,
    text: str,
    language: str,
    model: str,
    voice_id: str,
    sample_rate: int,
    context_id: str,
    continue_: bool = False,
) -> dict[str, Any]:
    language = str(language).lower().split("-", 1)[0]
    if language not in {"en", "fr", "es", "it", "zh"}:
        language = "en"
    return {
        "model_id": model,
        "transcript": text,
        "voice": {"mode": "id", "id": voice_id},
        "language": language,
        "context_id": context_id,
        "output_format": {
            "container": "raw",
            "encoding": "pcm_s16le",
            "sample_rate": sample_rate,
        },
        "add_timestamps": False,
        "continue": continue_,
    }


class CartesiaTTS(BaseTTS):
    """Keep one Cartesia socket warm and stream raw PCM directly to Shokz."""

    def __init__(
        self,
        *,
        api_key_env: str = "CARTESIA_API_KEY",
        model: str = "sonic-3.5",
        voice_id: str,
        api_version: str = "2026-03-01",
        output_device_name: str = "Shokz OpenComm2 UC",
        sample_rate: int = 24000,
        response_timeout_s: float = 15.0,
    ) -> None:
        self._api_key_env = api_key_env
        self._model = model
        self._voice_id = voice_id
        self._api_version = api_version
        self._output_device_name = output_device_name
        self._sample_rate = sample_rate
        self._response_timeout_s = response_timeout_s
        self._connection = None
        self._lock = threading.Lock()
        self.playback_started = False
        self.last_first_audio_ms: float | None = None
        self.last_total_ms: float | None = None
        self._utterance_context_id: str | None = None
        self._utterance_language = "en"
        self._utterance_thread: threading.Thread | None = None
        self._utterance_player = None
        self._utterance_error: Exception | None = None
        self._utterance_segment_count = 0
        self._utterance_started_at: float | None = None
        self._utterance_completed = False

    def _connect(self):
        from websockets.sync.client import connect

        api_key = os.getenv(self._api_key_env)
        if not api_key:
            raise RuntimeError(f"missing API key in {self._api_key_env}")
        return connect(
            build_cartesia_url(self._api_version),
            additional_headers={"X-API-Key": api_key},
            open_timeout=8,
            close_timeout=2,
            max_size=2**22,
        )

    def _ensure_connection(self):
        if self._connection is None:
            self._connection = self._connect()
        return self._connection

    def warm_up(self) -> None:
        try:
            from websockets.sync.client import connect  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Cartesia WebSocket support is unavailable; "
                "install the ATLAS audio-cloud extra"
            ) from exc
        with self._lock:
            self._ensure_connection()
        logger.info(
            "Cartesia %s ready (voice=%s, %d Hz)",
            self._model,
            self._voice_id,
            self._sample_rate,
        )

    def cue(self) -> bool:
        return play_pcm(
            listening_cue_pcm(),
            self._output_device_name,
            sample_rate=16000,
        )

    def begin_utterance(self, language: str = "en") -> bool:
        """Open one prosody context for every sentence in an LLM answer."""
        with self._lock:
            if self._utterance_context_id is not None:
                raise RuntimeError("a Cartesia utterance is already active")
            self._ensure_connection()
            self._utterance_context_id = str(uuid.uuid4())
            self._utterance_language = language
            self._utterance_thread = None
            self._utterance_player = None
            self._utterance_error = None
            self._utterance_segment_count = 0
            self._utterance_started_at = None
            self._utterance_completed = False
            self.playback_started = False
            self.last_first_audio_ms = None
            self.last_total_ms = None
        return True

    def _receive_utterance(self, context_id: str) -> None:
        player = None
        try:
            connection = self._ensure_connection()
            while True:
                raw = connection.recv(timeout=self._response_timeout_s)
                payload = json.loads(raw)
                if payload.get("context_id") != context_id:
                    continue
                message_type = payload.get("type")
                if message_type == "error":
                    raise RuntimeError(
                        payload.get("message")
                        or payload.get("title")
                        or "TTS error"
                    )
                if message_type == "chunk" and payload.get("data"):
                    if player is None:
                        player = open_raw_player(
                            self._output_device_name,
                            self._sample_rate,
                        )
                        self._utterance_player = player
                        self.playback_started = True
                        started = self._utterance_started_at or time.perf_counter()
                        self.last_first_audio_ms = (
                            time.perf_counter() - started
                        ) * 1000.0
                    if player.stdin is None:
                        raise RuntimeError("audio player stdin is unavailable")
                    player.stdin.write(base64.b64decode(payload["data"]))
                if payload.get("done") or message_type == "done":
                    break
            self._utterance_completed = bool(
                player and finish_raw_player(player, timeout_s=30)
            )
        except Exception as exc:
            self._utterance_error = exc
            if player is not None:
                try:
                    finish_raw_player(player, timeout_s=2)
                except Exception:
                    pass
        finally:
            started = self._utterance_started_at
            if started is not None:
                self.last_total_ms = (time.perf_counter() - started) * 1000.0

    def speak_segment(self, text: str, language: str = "en") -> bool:
        text = text.strip()
        if not text:
            return False
        with self._lock:
            context_id = self._utterance_context_id
        if context_id is None:
            return self.speak(text, language)
        with self._lock:
            if self._utterance_error is not None:
                return False
            if self._utterance_segment_count == 0:
                self._utterance_started_at = time.perf_counter()
                logger.info(
                    "[Cartesia] Continuous synthesis started "
                    "[model=%s language=%s]",
                    self._model,
                    self._utterance_language,
                )
            request = build_cartesia_request(
                text=text + " ",
                language=self._utterance_language,
                model=self._model,
                voice_id=self._voice_id,
                sample_rate=self._sample_rate,
                context_id=context_id,
                continue_=True,
            )
            try:
                self._ensure_connection().send(json.dumps(request))
            except Exception:
                if self._utterance_segment_count != 0 or self.playback_started:
                    raise
                logger.warning(
                    "[Cartesia] Socket stale before playback; reconnecting once"
                )
                self._close_connection()
                self._ensure_connection().send(json.dumps(request))
            self._utterance_segment_count += 1
            if self._utterance_thread is None:
                self._utterance_thread = threading.Thread(
                    target=self._receive_utterance,
                    args=(context_id,),
                    name="atlas-cartesia-stream",
                    daemon=True,
                )
                self._utterance_thread.start()
        return True

    def end_utterance(self) -> bool:
        with self._lock:
            context_id = self._utterance_context_id
            thread = self._utterance_thread
            if context_id is None or self._utterance_segment_count == 0:
                self._utterance_context_id = None
                return False
            if self._utterance_error is None:
                request = build_cartesia_request(
                    text="",
                    language=self._utterance_language,
                    model=self._model,
                    voice_id=self._voice_id,
                    sample_rate=self._sample_rate,
                    context_id=context_id,
                    continue_=False,
                )
                try:
                    self._ensure_connection().send(json.dumps(request))
                except Exception as exc:
                    self._utterance_error = exc
                    self._close_connection()

        if thread is not None:
            thread.join(timeout=self._response_timeout_s + 30)
            if thread.is_alive():
                self._utterance_error = RuntimeError(
                    "Cartesia continuous synthesis timed out"
                )
                self._close_connection()
                thread.join(timeout=2)

        with self._lock:
            error = self._utterance_error
            completed = self._utterance_completed and error is None
            logger.info(
                "[Cartesia] Continuous synthesis complete "
                "[segments=%d first_audio_ms=%s total_ms=%s audio_played=%s]",
                self._utterance_segment_count,
                (
                    f"{self.last_first_audio_ms:.0f}"
                    if self.last_first_audio_ms is not None
                    else "n/a"
                ),
                (
                    f"{self.last_total_ms:.0f}"
                    if self.last_total_ms is not None
                    else "n/a"
                ),
                completed,
            )
            if error is not None:
                logger.error("[Cartesia] Continuous TTS failed: %s", error)
            self._utterance_context_id = None
            self._utterance_thread = None
            self._utterance_player = None
            return completed

    def abort_utterance(self) -> None:
        with self._lock:
            thread = self._utterance_thread
            player = self._utterance_player
            self._utterance_context_id = None
            self._close_connection()
        if player is not None and player.poll() is None:
            player.kill()
        if thread is not None and thread.is_alive():
            thread.join(timeout=2)
        with self._lock:
            self._utterance_thread = None
            self._utterance_player = None

    def _speak_once(self, text: str, language: str) -> bool:
        started = time.perf_counter()
        self.last_first_audio_ms = None
        self.last_total_ms = None
        self.playback_started = False
        connection = self._ensure_connection()
        logger.info(
            "[Cartesia] Synthesis started [model=%s language=%s chars=%d]",
            self._model,
            language,
            len(text),
        )
        context_id = str(uuid.uuid4())
        request = build_cartesia_request(
            text=text,
            language=language,
            model=self._model,
            voice_id=self._voice_id,
            sample_rate=self._sample_rate,
            context_id=context_id,
        )
        connection.send(json.dumps(request))
        player = None
        try:
            while True:
                raw = connection.recv(timeout=self._response_timeout_s)
                payload = json.loads(raw)
                if payload.get("context_id") != context_id:
                    continue
                message_type = payload.get("type")
                if message_type == "error":
                    raise RuntimeError(
                        payload.get("message")
                        or payload.get("title")
                        or "TTS error"
                    )
                if message_type == "chunk" and payload.get("data"):
                    if player is None:
                        player = open_raw_player(
                            self._output_device_name,
                            self._sample_rate,
                        )
                        self.playback_started = True
                        self.last_first_audio_ms = (
                            time.perf_counter() - started
                        ) * 1000.0
                    if player.stdin is None:
                        raise RuntimeError("audio player stdin is unavailable")
                    player.stdin.write(base64.b64decode(payload["data"]))
                if payload.get("done") or message_type == "done":
                    break
            completed = bool(player and finish_raw_player(player))
            logger.info(
                "[Cartesia] Synthesis complete [first_audio_ms=%s total_ms=%.0f "
                "audio_played=%s]",
                (
                    f"{self.last_first_audio_ms:.0f}"
                    if self.last_first_audio_ms is not None
                    else "n/a"
                ),
                (time.perf_counter() - started) * 1000.0,
                completed,
            )
            return completed
        except Exception:
            if player is not None:
                try:
                    finish_raw_player(player, timeout_s=2)
                except Exception:
                    pass
            raise
        finally:
            self.last_total_ms = (time.perf_counter() - started) * 1000.0

    def speak(self, text: str, language: str = "en") -> bool:
        if not text.strip():
            return False
        with self._lock:
            for attempt in range(2):
                try:
                    return self._speak_once(text.strip(), language)
                except Exception as exc:
                    audio_started = self.playback_started
                    self._close_connection()
                    if attempt == 0 and not audio_started:
                        logger.warning(
                            "[Cartesia] Socket stale before playback; reconnecting once"
                        )
                        continue
                    logger.error("[Cartesia] TTS failed: %s", exc)
                    return False
            return False

    def _close_connection(self) -> None:
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    def close(self) -> None:
        self.abort_utterance()
        with self._lock:
            self._close_connection()
