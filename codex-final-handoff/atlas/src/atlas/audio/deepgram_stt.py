"""Deepgram Nova-3 streaming STT with local Silero endpointing."""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from .devices import find_sounddevice_input
from .silero_vad import SileroVAD
from .stt import BaseSTT, TranscriptResult

logger = logging.getLogger(__name__)


class DeepgramError(RuntimeError):
    """Raised when a question was captured but Deepgram could not answer."""


@dataclass(frozen=True)
class DeepgramResult:
    text: str
    confidence: float
    language: str
    is_final: bool
    speech_final: bool
    from_finalize: bool


def build_deepgram_url(
    *,
    model: str,
    language: str,
    sample_rate: int,
    channels: int,
    endpointing_ms: int,
    keyterms: list[str],
) -> str:
    parameters: list[tuple[str, str]] = [
        ("model", model),
        ("language", language),
        ("encoding", "linear16"),
        ("sample_rate", str(sample_rate)),
        ("channels", str(channels)),
        ("punctuate", "true"),
        ("smart_format", "true"),
        ("interim_results", "true"),
        ("endpointing", str(endpointing_ms)),
        ("vad_events", "true"),
        ("mip_opt_out", "true"),
    ]
    parameters.extend(("keyterm", term) for term in keyterms if term.strip())
    return "wss://api.deepgram.com/v1/listen?" + urlencode(parameters)


def parse_deepgram_result(
    payload: dict[str, Any],
    *,
    default_language: str = "en",
) -> DeepgramResult | None:
    if payload.get("type") != "Results":
        return None
    alternatives = payload.get("channel", {}).get("alternatives", [])
    if not alternatives:
        return None
    alternative = alternatives[0]
    words = alternative.get("words") or []
    languages = alternative.get("languages") or []
    language = languages[0] if languages else ""
    if not language and words:
        language = words[0].get("language", "")
    language = str(language or default_language).split("-", 1)[0].lower()
    return DeepgramResult(
        text=str(alternative.get("transcript", "")).strip(),
        confidence=float(alternative.get("confidence", 0.0) or 0.0),
        language=language,
        is_final=bool(payload.get("is_final")),
        speech_final=bool(payload.get("speech_final")),
        from_finalize=bool(payload.get("from_finalize")),
    )


class DeepgramSTT(BaseSTT):
    """Stream only the current question; audio remains in memory, never on disk."""

    _FRAME_SAMPLES = 512

    def __init__(
        self,
        *,
        api_key_env: str = "DEEPGRAM_API_KEY",
        model: str = "nova-3",
        language: str = "multi",
        input_device_name: str = "Shokz OpenComm2 UC",
        sample_rate: int = 16000,
        channels: int = 1,
        endpointing_ms: int = 400,
        vad_threshold: float = 0.5,
        min_speech_ms: int = 250,
        min_silence_ms: int = 650,
        pre_roll_ms: int = 250,
        final_timeout_s: float = 3.0,
        silero_model_path: str = "models/silero_vad.onnx",
        keyterms: list[str] | None = None,
        vad: SileroVAD | None = None,
        log_live_transcripts: bool = False,
    ) -> None:
        self._api_key_env = api_key_env
        self._model = model
        self._language = language
        self._input_device_name = input_device_name
        self._sample_rate = sample_rate
        self._channels = channels
        self._endpointing_ms = endpointing_ms
        self._min_speech_ms = min_speech_ms
        self._min_silence_ms = min_silence_ms
        self._pre_roll_ms = pre_roll_ms
        self._final_timeout_s = final_timeout_s
        self._keyterms = list(keyterms or [])
        self._log_live_transcripts = log_live_transcripts
        self._vad = vad or SileroVAD(
            vad_threshold,
            sample_rate,
            model_path=silero_model_path,
        )
        self._input_device: int | None = None
        self._ready = False
        self._prepared_connection = None
        self.last_audio_pcm = b""

    def warm_up(self) -> None:
        if self._ready:
            return
        if not os.getenv(self._api_key_env):
            raise RuntimeError(f"missing API key in {self._api_key_env}")
        try:
            import sounddevice  # noqa: F401  # type: ignore
            from websockets.sync.client import connect  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Deepgram streaming dependencies are unavailable; "
                "install the ATLAS audio-cloud extra"
            ) from exc
        self._vad.warm_up()
        self._input_device = find_sounddevice_input(self._input_device_name)
        if self._input_device is None:
            logger.warning(
                "Audio input %r not found; using system default",
                self._input_device_name,
            )
        self._ready = True
        logger.info("Deepgram %s ready with local Silero VAD", self._model)

    def _connect(self):
        from websockets.sync.client import connect

        api_key = os.getenv(self._api_key_env)
        if not api_key:
            raise DeepgramError(f"missing API key in {self._api_key_env}")
        url = build_deepgram_url(
            model=self._model,
            language=self._language,
            sample_rate=self._sample_rate,
            channels=self._channels,
            endpointing_ms=self._endpointing_ms,
            keyterms=self._keyterms,
        )
        return connect(
            url,
            additional_headers={"Authorization": f"Token {api_key}"},
            open_timeout=8,
            close_timeout=2,
            max_size=2**20,
        )

    def prepare_listen(self) -> None:
        """Open the question socket before the cue so recording starts at once."""
        if not self._ready:
            self.warm_up()
        if self._prepared_connection is not None:
            try:
                self._prepared_connection.close()
            except Exception:
                pass
        self._prepared_connection = self._connect()

    def set_language(self, language: str) -> None:
        normalized = str(language).split("-", 1)[0].lower()
        if normalized not in {"en", "fr", "es", "it", "zh", "multi"}:
            normalized = "multi"
        if normalized == self._language:
            return
        if self._prepared_connection is not None:
            try:
                self._prepared_connection.close()
            except Exception:
                pass
            self._prepared_connection = None
        self._language = normalized

    @staticmethod
    def _receiver(
        connection,
        messages: queue.Queue[dict[str, Any]],
        *,
        log_live_transcripts: bool = False,
        default_language: str = "en",
        listen_started_at: float | None = None,
    ) -> None:
        last_logged_text = ""
        first_result_logged = False
        try:
            while True:
                raw = connection.recv()
                if raw is None:
                    return
                payload = json.loads(raw)
                messages.put(payload)
                if log_live_transcripts:
                    result = parse_deepgram_result(
                        payload,
                        default_language=default_language,
                    )
                    if (
                        result is not None
                        and result.text
                        and result.text != last_logged_text
                    ):
                        logger.info(
                            "[STT live] %s [language=%s final=%s confidence=%.2f]",
                            result.text,
                            result.language,
                            result.is_final,
                            result.confidence,
                        )
                        if not first_result_logged and listen_started_at is not None:
                            logger.info(
                                "[Timing] Deepgram first interim %.0f ms",
                                (time.perf_counter() - listen_started_at) * 1000.0,
                            )
                            first_result_logged = True
                        last_logged_text = result.text
                if payload.get("type") == "Metadata":
                    return
        except Exception as exc:
            messages.put({"type": "_error", "message": str(exc)})

    def listen(self, duration_s: float = 5.0) -> TranscriptResult | None:
        if not self._ready:
            self.warm_up()

        import sounddevice as sd  # type: ignore

        started = time.perf_counter()
        self.last_audio_pcm = b""
        self._vad.reset()
        connection = None
        receiver: threading.Thread | None = None
        messages: queue.Queue[dict[str, Any]] = queue.Queue()
        sent_frames: list[bytes] = []
        frame_ms = 1000.0 * self._FRAME_SAMPLES / self._sample_rate
        pre_roll_frames = max(1, int(self._pre_roll_ms / frame_ms))
        pre_roll: deque[bytes] = deque(maxlen=pre_roll_frames)
        speech_started = False
        speech_started_at = 0.0
        last_voice_at = 0.0

        try:
            connection = self._prepared_connection or self._connect()
            self._prepared_connection = None
            default_language = self._language if self._language != "multi" else "en"
            receiver = threading.Thread(
                target=self._receiver,
                args=(connection, messages),
                kwargs={
                    "log_live_transcripts": self._log_live_transcripts,
                    "default_language": default_language,
                    "listen_started_at": started,
                },
                name="atlas-deepgram-receiver",
                daemon=True,
            )
            receiver.start()
            logger.info(
                "[Deepgram] Listening [model=%s language=%s timeout=%.1fs]",
                self._model,
                self._language,
                duration_s,
            )

            deadline = time.monotonic() + duration_s
            with sd.RawInputStream(
                samplerate=self._sample_rate,
                blocksize=self._FRAME_SAMPLES,
                channels=self._channels,
                dtype="int16",
                device=self._input_device,
            ) as stream:
                while time.monotonic() < deadline:
                    raw, overflowed = stream.read(self._FRAME_SAMPLES)
                    if overflowed:
                        logger.debug("Microphone input overflow during question")
                    pcm = bytes(raw)
                    probability = self._vad.probability(pcm)
                    now = time.monotonic()

                    if not speech_started:
                        pre_roll.append(pcm)
                        if probability < self._vad.threshold:
                            continue
                        speech_started = True
                        speech_started_at = now
                        last_voice_at = now
                        logger.info(
                            "[Silero VAD] Speech started "
                            "[probability=%.2f threshold=%.2f]",
                            probability,
                            self._vad.threshold,
                        )
                        for buffered in pre_roll:
                            connection.send(buffered)
                            sent_frames.append(buffered)
                        pre_roll.clear()
                        continue

                    connection.send(pcm)
                    sent_frames.append(pcm)
                    if probability >= self._vad.threshold:
                        last_voice_at = now

                    speech_ms = (now - speech_started_at) * 1000.0
                    silence_ms = (now - last_voice_at) * 1000.0
                    if (
                        speech_ms >= self._min_speech_ms
                        and silence_ms >= self._min_silence_ms
                    ):
                        break

            self.last_audio_pcm = b"".join(sent_frames)
            if not speech_started:
                connection.send(json.dumps({"type": "CloseStream"}))
                logger.info("[Silero VAD] No speech detected before timeout")
                return None

            connection.send(json.dumps({"type": "Finalize"}))
            final_parts: list[str] = []
            interim_text = ""
            confidences: list[float] = []
            detected_language = "en"
            final_deadline = time.monotonic() + self._final_timeout_s
            while time.monotonic() < final_deadline:
                try:
                    payload = messages.get(timeout=0.2)
                except queue.Empty:
                    continue
                if payload.get("type") == "_error":
                    raise DeepgramError(str(payload.get("message", "socket error")))
                result = parse_deepgram_result(
                    payload,
                    default_language=default_language,
                )
                if result is None:
                    continue
                if result.text:
                    interim_text = result.text
                    detected_language = result.language or detected_language
                if result.is_final and result.text:
                    if not final_parts or final_parts[-1] != result.text:
                        final_parts.append(result.text)
                        confidences.append(result.confidence)
                if result.from_finalize:
                    break

            text = " ".join(final_parts).strip() or interim_text.strip()
            if not text:
                logger.info(
                    "[Deepgram] No transcript returned; treating capture as noise"
                )
                return None
            confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )
            return TranscriptResult(
                text=text,
                language=detected_language,
                confidence=confidence,
                duration_ms=(time.perf_counter() - started) * 1000.0,
            )
        except DeepgramError as exc:
            logger.error("[Deepgram] Transcription failed: %s", exc)
            raise
        except Exception as exc:
            logger.error("[Deepgram] Capture or connection failed: %s", exc)
            raise DeepgramError(str(exc)) from exc
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
            if receiver is not None:
                receiver.join(timeout=0.5)

    def close(self) -> None:
        if self._prepared_connection is not None:
            try:
                self._prepared_connection.close()
            except Exception:
                pass
            self._prepared_connection = None
        self._ready = False
        self.last_audio_pcm = b""
