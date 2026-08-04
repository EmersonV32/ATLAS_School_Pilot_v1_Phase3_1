"""Small stateful wrapper around the local Silero voice activity detector."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SileroVAD:
    """Return speech probabilities for 16-bit mono PCM frames.

    Silero expects 512 samples per frame at 16 kHz. ATLAS records using that
    exact block size, which avoids resampling and keeps endpointing cheap.
    """

    def __init__(
        self,
        threshold: float = 0.5,
        sample_rate: int = 16000,
        model_path: str = "models/silero_vad.onnx",
        session: Any | None = None,
    ) -> None:
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.model_path = Path(model_path).expanduser()
        self._session = session
        self._state = None
        self._context = None

    def warm_up(self) -> None:
        if self._session is not None:
            self.reset()
            return
        if self.sample_rate != 16000:
            raise ValueError("Silero VAD currently requires a 16 kHz input")
        try:
            import onnxruntime as ort  # type: ignore

            if not self.model_path.is_file():
                raise FileNotFoundError(
                    f"Silero ONNX model not found: {self.model_path}"
                )
            options = ort.SessionOptions()
            options.inter_op_num_threads = 1
            options.intra_op_num_threads = 1
            self._session = ort.InferenceSession(
                str(self.model_path),
                providers=["CPUExecutionProvider"],
                sess_options=options,
            )
            self.reset()
            logger.info(
                "Silero VAD ready (%s, threshold=%.2f)",
                self.model_path,
                self.threshold,
            )
        except ImportError as exc:
            raise RuntimeError(
                "ONNX Runtime is unavailable; install the ATLAS audio-cloud extra"
            ) from exc

    def reset(self) -> None:
        import numpy as np  # type: ignore

        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, 64), dtype=np.float32)

    def probability(self, pcm_s16le: bytes) -> float:
        if self._session is None:
            self.warm_up()
        import numpy as np  # type: ignore

        samples = np.frombuffer(pcm_s16le, dtype="<i2").astype(np.float32)
        if samples.size != 512:
            raise ValueError(
                f"Silero VAD needs 512 samples at 16 kHz, got {samples.size}"
            )
        current = (samples / 32768.0).reshape(1, -1)
        model_input = np.concatenate((self._context, current), axis=1)
        output, self._state = self._session.run(
            None,
            {
                "input": model_input,
                "state": self._state,
                "sr": np.array(self.sample_rate, dtype=np.int64),
            },
        )
        self._context = model_input[:, -64:]
        return float(np.asarray(output).reshape(-1)[0])

    def is_speech(self, pcm_s16le: bytes) -> bool:
        return self.probability(pcm_s16le) >= self.threshold
