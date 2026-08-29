"""Piper TTS adapter. Calls piper binary via subprocess."""
from __future__ import annotations
import logging
import shutil
import subprocess
from .tts import BaseTTS

logger = logging.getLogger(__name__)


class PiperTTS(BaseTTS):
    """
    Requires: piper binary on PATH + downloaded .onnx voice models.
    Download voices from: https://github.com/rhasspy/piper/releases
      EN: en_US-amy-medium.onnx
      FR: fr_FR-mls-medium.onnx
    Place them in atlas/voices/
    """

    def __init__(
        self,
        voice_en: str = "voices/en_US-amy-medium.onnx",
        voice_fr: str = "voices/fr_FR-mls-medium.onnx",
        piper_binary: str = "piper",
    ) -> None:
        self._voices = {"en": voice_en, "fr": voice_fr}
        self._binary = piper_binary

    def speak(self, text: str, language: str = "en") -> bool:
        if not shutil.which(self._binary):
            logger.error("Piper binary not found on PATH — see README for install steps")
            return False
        voice = self._voices.get(language, self._voices["en"])
        try:
            # Piper writes raw PCM to stdout; pipe to aplay on Jetson.
            # Generated audio is played and discarded — never written to disk.
            piper_proc = subprocess.run(
                [self._binary, "--model", voice, "--output-raw"],
                input=text.encode(),
                capture_output=True,
                timeout=10,
            )
            if piper_proc.returncode != 0 or not piper_proc.stdout:
                logger.warning("Piper synthesis failed (rc=%s)", piper_proc.returncode)
                return False
            subprocess.run(
                ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
                input=piper_proc.stdout,
                timeout=15,
            )
            return True
        except subprocess.TimeoutExpired:
            logger.warning("TTS timed out for text: %.40s...", text)
            return False
        except Exception as exc:
            logger.warning("TTS error: %s", exc)
            return False
