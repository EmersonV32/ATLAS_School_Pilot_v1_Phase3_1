"""faster-whisper STT adapter. Lazy import — safe to import on any OS."""
from __future__ import annotations
import logging
import time
from typing import Optional
from .stt import BaseSTT, TranscriptResult

logger = logging.getLogger(__name__)


class WhisperSTT(BaseSTT):
    """
    Requires:  pip install faster-whisper sounddevice numpy
    model_size:   "tiny" for Orin Nano, "small" for Orin NX (recommended).
    device:       "auto" picks cuda when available, else cpu.
    compute_type: "int8" is a good Jetson default; "float16" on desktop GPU.
    """

    def __init__(
        self,
        model_size: str = "small",
        device: str = "auto",
        compute_type: str = "int8",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None

    def _load(self) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
            logger.info(
                "Whisper '%s' loaded on %s (%s)",
                self._model_size, self._device, self._compute_type,
            )
        except ImportError:
            logger.error("faster-whisper not installed — run: pip install faster-whisper")
            raise

    def listen(self, duration_s: float = 5.0) -> Optional[TranscriptResult]:
        if self._model is None:
            try:
                self._load()
            except ImportError:
                return None
        started = time.perf_counter()
        try:
            import io
            import sounddevice as sd  # type: ignore
            audio = sd.rec(int(duration_s * 16000), samplerate=16000, channels=1, dtype="float32")
            sd.wait()
            audio_bytes = (audio * 32767).astype("int16").tobytes()
            segments, info = self._model.transcribe(io.BytesIO(audio_bytes), beam_size=5)
            text = " ".join(s.text for s in segments).strip()
            if not text:
                return None
            return TranscriptResult(
                text=text,
                language=info.language,
                confidence=float(info.language_probability),
                duration_ms=(time.perf_counter() - started) * 1000.0,
            )
        except Exception as exc:
            logger.warning("STT failed: %s", exc)
            return None
