"""faster-whisper STT adapter with Shokz USB microphone selection."""

from __future__ import annotations

import logging
import time

from atlas.models.languages import ADMIN_LANGUAGE_CODES

from .devices import find_sounddevice_input
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
