"""faster-whisper STT adapter. Lazy import — safe to import on any OS."""
from __future__ import annotations
import logging
from typing import Optional
from .stt import BaseSTT, TranscriptResult

logger = logging.getLogger(__name__)


class WhisperSTT(BaseSTT):
    """
    Requires:  pip install faster-whisper sounddevice numpy
    model_size: "tiny" for Orin Nano, "small" for Orin NX (recommended).
    device:     "cuda" on Jetson, "cpu" on dev machine.
    """

    def __init__(self, model_size: str = "small", device: str = "cuda") -> None:
        self._model_size = model_size
        self._device = device
        self._model = None

    def _load(self) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore
            self._model = WhisperModel(self._model_size, device=self._device, compute_type="float16")
            logger.info("Whisper '%s' loaded on %s", self._model_size, self._device)
        except ImportError:
            logger.error("faster-whisper not installed — run: pip install faster-whisper")
            raise

    def listen(self, duration_s: float = 5.0) -> Optional[TranscriptResult]:
        if self._model is None:
            self._load()
        try:
            import io
            import sounddevice as sd  # type: ignore
            import numpy as np        # type: ignore
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
            )
        except Exception as exc:
            logger.warning("STT failed: %s", exc)
            return None
