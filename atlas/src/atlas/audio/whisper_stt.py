"""faster-whisper STT adapter with Shokz USB microphone selection."""

from __future__ import annotations

import logging
import time
from collections import deque

from atlas.models.languages import ADMIN_LANGUAGE_CODES

from .devices import find_sounddevice_input
from .silero_vad import SileroVAD
from .stt import BaseSTT, TranscriptResult

logger = logging.getLogger(__name__)


class WhisperSTT(BaseSTT):
    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        input_device_name: str = "Shokz OpenComm2 UC",
        sample_rate: int = 16000,
        channels: int = 1,
        beam_size: int = 5,
        local_files_only: bool = True,
        vad_threshold: float = 0.5,
        silero_model_path: str = "models/silero_vad.onnx",
        min_speech_ms: int = 250,
        min_silence_ms: int = 1200,
        pre_roll_ms: int = 250,
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._input_device_name = input_device_name
        self._sample_rate = sample_rate
        self._channels = channels
        self._beam_size = beam_size
        self._local_files_only = local_files_only
        self._model = None
        self._input_device: int | None = None
        self._language: str | None = None
        self._vad = SileroVAD(
            vad_threshold,
            sample_rate,
            model_path=silero_model_path,
        )
        self._vad_ready = False
        self._min_speech_ms = max(0, min_speech_ms)
        self._min_silence_ms = max(0, min_silence_ms)
        self._pre_roll_ms = max(0, pre_roll_ms)

    def set_language(self, language: str) -> None:
        normalized = str(language).split("-", 1)[0].lower()
        self._language = (
            normalized if normalized in ADMIN_LANGUAGE_CODES else None
        )

    def warm_up(self) -> None:
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel  # type: ignore

            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
                local_files_only=self._local_files_only,
            )
            self._input_device = find_sounddevice_input(self._input_device_name)
            if self._input_device is None:
                logger.warning(
                    "Audio input %r not found; using system default",
                    self._input_device_name,
                )
            logger.info(
                "Whisper %s ready on %s (%s), input=%s",
                self._model_size,
                self._device,
                self._compute_type,
                self._input_device,
            )
            try:
                self._vad.warm_up()
                self._vad_ready = True
            except Exception as exc:
                logger.warning(
                    "Silero endpointing unavailable; Whisper will use the full "
                    "listen window: %s",
                    exc,
                )
        except ImportError:
            logger.error("faster-whisper and sounddevice are required")
            raise

    def listen(self, duration_s: float = 5.0) -> TranscriptResult | None:
        if self._model is None:
            try:
                self.warm_up()
            except Exception as exc:
                logger.warning("Whisper startup failed: %s", exc)
                return None
        started = time.perf_counter()
        try:
            import numpy as np  # type: ignore
            import sounddevice as sd  # type: ignore

            if self._vad_ready and self._sample_rate == 16000 and self._channels == 1:
                pcm = self._record_until_silence(sd, duration_s)
                if not pcm:
                    return None
                mono = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
            else:
                audio = sd.rec(
                    int(duration_s * self._sample_rate),
                    samplerate=self._sample_rate,
                    channels=self._channels,
                    dtype="float32",
                    device=self._input_device,
                )
                sd.wait()
                mono = np.asarray(audio, dtype=np.float32).reshape(-1)
            return self._transcribe(mono, started=started)
        except Exception as exc:
            logger.warning("STT failed: %s", exc)
            return None

    def _record_until_silence(self, sounddevice, duration_s: float) -> bytes:
        """Record one local utterance and stop after speech-ending silence."""
        frame_samples = 512
        frame_ms = 1000.0 * frame_samples / self._sample_rate
        pre_roll_frames = max(1, int(self._pre_roll_ms / frame_ms))
        speech_confirmation_frames = max(1, int(self._min_speech_ms / frame_ms))
        pre_roll = deque(maxlen=pre_roll_frames + speech_confirmation_frames)
        captured: list[bytes] = []
        speech_started = False
        speech_ms = 0.0
        silence_ms = 0.0
        self._vad.reset()
        deadline = time.monotonic() + duration_s
        with sounddevice.RawInputStream(
            samplerate=self._sample_rate,
            blocksize=frame_samples,
            channels=1,
            dtype="int16",
            device=self._input_device,
        ) as stream:
            while time.monotonic() < deadline:
                frame, overflowed = stream.read(frame_samples)
                if overflowed:
                    logger.warning("Whisper input overflow detected")
                pcm = bytes(frame)
                speech = self._vad.is_speech(pcm)
                if not speech_started:
                    pre_roll.append(pcm)
                    speech_ms = speech_ms + frame_ms if speech else 0.0
                    if speech_ms >= self._min_speech_ms:
                        speech_started = True
                        captured.extend(pre_roll)
                        silence_ms = 0.0
                    continue
                captured.append(pcm)
                silence_ms = 0.0 if speech else silence_ms + frame_ms
                if silence_ms >= self._min_silence_ms:
                    break
        return b"".join(captured)

    def transcribe_pcm(self, pcm: bytes) -> TranscriptResult | None:
        """Recover a cloud-failed question without asking the visitor to repeat it."""
        if not pcm:
            return None
        if self._model is None:
            self.warm_up()
        import numpy as np  # type: ignore

        started = time.perf_counter()
        mono = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        return self._transcribe(mono, started=started)

    def _transcribe(
        self,
        mono,
        *,
        started: float,
    ) -> TranscriptResult | None:
        segments, info = self._model.transcribe(
            mono,
            beam_size=self._beam_size,
            vad_filter=True,
            condition_on_previous_text=False,
            language=self._language,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if not text:
            return None
        return TranscriptResult(
            text=text,
            language=self._language or info.language,
            confidence=float(info.language_probability),
            duration_ms=(time.perf_counter() - started) * 1000.0,
        )
