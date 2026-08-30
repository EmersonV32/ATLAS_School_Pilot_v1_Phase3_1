"""Piper TTS adapter with automatic Shokz USB playback selection."""

from __future__ import annotations

import logging
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from .devices import find_alsa_playback, find_pulse_playback
from .playback import normalize_volume, scale_pcm_s16le
from .tts import BaseTTS

logger = logging.getLogger(__name__)


class PiperTTS(BaseTTS):
    def __init__(
        self,
        voice_en: str,
        voice_fr: str,
        voice_es: str = "",
        voice_it: str = "",
        voice_zh: str = "",
        piper_binary: str = "piper",
        output_device_name: str = "Shokz OpenComm2 UC",
        volume_percent: int = 100,
    ) -> None:
        self._voices = {
            "en": Path(voice_en).expanduser(),
            "fr": Path(voice_fr).expanduser(),
        }
        for language, voice in {
            "es": voice_es,
            "it": voice_it,
            "zh": voice_zh,
        }.items():
            if voice.strip():
                self._voices[language] = Path(voice).expanduser()
        self._binary = piper_binary
        self._output_device_name = output_device_name
        self._volume_percent = normalize_volume(volume_percent)
        self._command: list[str] | None = None

    def set_output_device(self, output_device_name: str) -> None:
        self._output_device_name = str(output_device_name).strip()

    def set_volume(self, volume_percent: int) -> None:
        self._volume_percent = normalize_volume(volume_percent)

    def audio_settings(self) -> dict[str, object]:
        return {
            "output_device_name": self._output_device_name,
            "volume_percent": self._volume_percent,
        }

    def _resolve_command(self) -> list[str]:
        if self._command is not None:
            return self._command
        explicit = Path(self._binary).expanduser()
        if explicit.is_file():
            self._command = [str(explicit)]
        elif shutil.which(self._binary):
            self._command = [self._binary]
        else:
            # piper-tts installs a Python module even on builds without a
            # console-script entry point.
            self._command = [sys.executable, "-m", "piper"]
        return self._command

    def _voice_for(self, language: str) -> Path:
        language = str(language).lower().split("-", 1)[0]
        voice = self._voices.get(language)
        if voice is not None:
            return voice
        logger.warning("No Piper voice configured for %s; using English", language)
        return self._voices["en"]

    def warm_up(self) -> None:
        for voice in self._voices.values():
            if not voice.is_file():
                raise FileNotFoundError(f"Piper voice not found: {voice}")
            config = Path(f"{voice}.json")
            if not config.is_file():
                raise FileNotFoundError(f"Piper voice config not found: {config}")
        # Resolve the executable now. The actual voice process starts on each
        # utterance because that path is the most portable Piper API.
        self._resolve_command()
        logger.info(
            "Piper voices ready: %s", ", ".join(map(str, self._voices.values()))
        )

    def _play_wav(self, output_path: str) -> bool:
        if self._volume_percent < 100:
            with wave.open(output_path, "rb") as wav_file:
                params = wav_file.getparams()
                frames = wav_file.readframes(wav_file.getnframes())
            if params.sampwidth == 2:
                frames = scale_pcm_s16le(frames, self._volume_percent)
                with wave.open(output_path, "wb") as wav_file:
                    wav_file.setparams(params)
                    wav_file.writeframes(frames)
        pulse_device = find_pulse_playback(self._output_device_name)
        if pulse_device and shutil.which("paplay"):
            playback = ["paplay", f"--device={pulse_device}", output_path]
        else:
            playback_device = find_alsa_playback(self._output_device_name)
            playback = ["aplay"]
            if playback_device:
                playback += ["-D", playback_device]
            playback.append(output_path)
        result = subprocess.run(playback, capture_output=True, timeout=30, check=False)
        if result.returncode != 0:
            logger.warning(
                "Audio playback failed: %s",
                result.stderr.decode("utf-8", errors="replace")[-300:],
            )
            return False
        return True

    def cue(self) -> bool:
        """Play an immediate two-note cue so the visitor knows to speak."""
        fd, output_path = tempfile.mkstemp(prefix="atlas-cue-", suffix=".wav")
        os.close(fd)
        try:
            sample_rate = 16000
            amplitude = int(7000 * self._volume_percent / 100.0)
            with wave.open(output_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                for frequency, duration in ((660.0, 0.09), (880.0, 0.12)):
                    count = int(sample_rate * duration)
                    frames = bytearray()
                    for index in range(count):
                        edge = min(index, count - index - 1, 80) / 80.0
                        sample = int(
                            amplitude
                            * max(0.0, edge)
                            * math.sin(2.0 * math.pi * frequency * index / sample_rate)
                        )
                        frames.extend(struct.pack("<h", sample))
                    wav_file.writeframes(frames)
            return self._play_wav(output_path)
        except Exception as exc:
            logger.warning("Listening cue failed: %s", exc)
            return False
        finally:
            Path(output_path).unlink(missing_ok=True)

    def speak(self, text: str, language: str = "en") -> bool:
        voice = self._voice_for(language)
        try:
            if self._command is None:
                self.warm_up()
            fd, output_path = tempfile.mkstemp(prefix="atlas-tts-", suffix=".wav")
            os.close(fd)
            try:
                synthesis = subprocess.run(
                    self._resolve_command()
                    + ["--model", str(voice), "--output-file", output_path],
                    input=(text.strip() + "\n").encode("utf-8"),
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                if synthesis.returncode != 0 or not Path(output_path).stat().st_size:
                    logger.warning(
                        "Piper synthesis failed: %s",
                        synthesis.stderr.decode("utf-8", errors="replace")[-300:],
                    )
                    return False
                return self._play_wav(output_path)
            finally:
                Path(output_path).unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("TTS error: %s", exc)
            return False
