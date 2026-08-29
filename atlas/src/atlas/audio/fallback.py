"""Resilient cloud-primary speech adapters with local offline fallbacks."""

from __future__ import annotations

import logging
import time

from .stt import BaseSTT, TranscriptResult
from .tts import BaseTTS

logger = logging.getLogger(__name__)


class FallbackSTT(BaseSTT):
    def __init__(
        self,
        primary: BaseSTT,
        fallback: BaseSTT,
        *,
        primary_retry_interval_s: float = 15.0,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.primary_ready = False
        self.fallback_ready = False
        self.last_provider: str | None = None
        self._primary_retry_interval_s = max(0.0, primary_retry_interval_s)
        self._primary_failed_at = 0.0

    def _mark_primary_failed(self) -> None:
        self.primary_ready = False
        self._primary_failed_at = time.monotonic()

    def _primary_retry_due(self) -> bool:
        return (
            not self.primary_ready
            and time.monotonic() - self._primary_failed_at
            >= self._primary_retry_interval_s
        )

    def warm_up(self) -> None:
        primary_error: Exception | None = None
        fallback_error: Exception | None = None
        try:
            self.primary.warm_up()
            self.primary_ready = True
            logger.info("[STT] Primary ready: %s", type(self.primary).__name__)
        except Exception as exc:
            primary_error = exc
            self._mark_primary_failed()
            logger.warning("Cloud STT unavailable; using local fallback: %s", exc)
        try:
            self.fallback.warm_up()
            self.fallback_ready = True
            logger.info("[STT] Fallback ready: %s", type(self.fallback).__name__)
        except Exception as exc:
            fallback_error = exc
            logger.warning("Local STT fallback unavailable: %s", exc)
        if not self.primary_ready and not self.fallback_ready:
            raise RuntimeError(
                "no STT provider is ready "
                f"(cloud={primary_error}, local={fallback_error})"
            )

    def listen(self, duration_s: float = 5.0) -> TranscriptResult | None:
        if self.primary_ready:
            try:
                result = self.primary.listen(duration_s)
                self.last_provider = type(self.primary).__name__
                logger.info("[STT] Provider used: %s", self.last_provider)
                return result
            except Exception as exc:
                self._mark_primary_failed()
                logger.warning(
                    "[STT] Primary %s failed; attempting %s recovery: %s",
                    type(self.primary).__name__,
                    type(self.fallback).__name__,
                    exc,
                )
                pcm = getattr(self.primary, "last_audio_pcm", b"")
                transcribe_pcm = getattr(self.fallback, "transcribe_pcm", None)
                if pcm and self.fallback_ready and callable(transcribe_pcm):
                    result = transcribe_pcm(pcm)
                    self.last_provider = type(self.fallback).__name__
                    logger.warning(
                        "[STT] Current question recovered by fallback: %s",
                        self.last_provider,
                    )
                    return result
                logger.error(
                    "[STT] Current question could not be recovered by fallback"
                )
                return None
        try:
            result = self.fallback.listen(duration_s)
            self.last_provider = type(self.fallback).__name__
            logger.info("[STT] Provider used: %s", self.last_provider)
            return result
        except Exception as exc:
            logger.error(
                "[STT] Fallback %s failed: %s",
                type(self.fallback).__name__,
                exc,
            )
            raise

    def set_language(self, language: str) -> None:
        self.primary.set_language(language)
        self.fallback.set_language(language)

    def prepare_listen(self) -> None:
        should_try_primary = self.primary_ready or self._primary_retry_due()
        if should_try_primary:
            was_unavailable = not self.primary_ready
            try:
                if was_unavailable:
                    self.primary.warm_up()
                self.primary.prepare_listen()
                self.primary_ready = True
                if was_unavailable:
                    logger.info(
                        "[STT] Primary recovered: %s",
                        type(self.primary).__name__,
                    )
                return
            except Exception as exc:
                self._mark_primary_failed()
                logger.warning(
                    "[STT] Primary %s preparation failed; using %s: %s",
                    type(self.primary).__name__,
                    type(self.fallback).__name__,
                    exc,
                )
        if self.fallback_ready:
            self.fallback.prepare_listen()

    def close(self) -> None:
        self.primary.close()
        self.fallback.close()

    def provider_status(self) -> str:
        active = self.last_provider or "not used yet"
        return (
            f"{type(self.primary).__name__} primary "
            f"({'ready' if self.primary_ready else 'unavailable'}); "
            f"{type(self.fallback).__name__} fallback "
            f"({'ready' if self.fallback_ready else 'unavailable'}); "
            f"last={active}"
        )


class FallbackTTS(BaseTTS):
    def __init__(self, primary: BaseTTS, fallback: BaseTTS) -> None:
        self.primary = primary
        self.fallback = fallback
        self.primary_ready = False
        self.fallback_ready = False
        self.last_provider: str | None = None
        self._last_adapter: BaseTTS | None = None
        self._streaming_primary = False
        self._stream_segments: list[str] = []
        self._stream_language = "en"

    def warm_up(self) -> None:
        primary_error: Exception | None = None
        fallback_error: Exception | None = None
        try:
            self.primary.warm_up()
            self.primary_ready = True
            logger.info("[TTS] Primary ready: %s", type(self.primary).__name__)
        except Exception as exc:
            primary_error = exc
            logger.warning("Cloud TTS unavailable; using local fallback: %s", exc)
        try:
            self.fallback.warm_up()
            self.fallback_ready = True
            logger.info("[TTS] Fallback ready: %s", type(self.fallback).__name__)
        except Exception as exc:
            fallback_error = exc
            logger.warning("Local TTS fallback unavailable: %s", exc)
        if not self.primary_ready and not self.fallback_ready:
            raise RuntimeError(
                "no TTS provider is ready "
                f"(cloud={primary_error}, local={fallback_error})"
            )

    def cue(self) -> bool:
        provider = self.primary if self.primary_ready else self.fallback
        return provider.cue()

    def begin_utterance(self, language: str = "en") -> bool:
        self._streaming_primary = False
        self._stream_segments = []
        self._stream_language = language
        if not self.primary_ready:
            return False
        try:
            started = bool(self.primary.begin_utterance(language))
        except Exception as exc:
            logger.warning(
                "[TTS] Primary %s could not start continuous synthesis: %s",
                type(self.primary).__name__,
                exc,
            )
            return False
        self._streaming_primary = started
        return started

    def speak_segment(self, text: str, language: str = "en") -> bool:
        if not self._streaming_primary:
            return self.speak(text, language)
        self._stream_segments.append(text)
        try:
            return bool(self.primary.speak_segment(text, language))
        except Exception as exc:
            logger.error(
                "[TTS] Primary %s segment failed: %s",
                type(self.primary).__name__,
                exc,
            )
            return False

    def end_utterance(self) -> bool:
        if not self._streaming_primary:
            return False
        self._streaming_primary = False
        try:
            result = bool(self.primary.end_utterance())
        except Exception as exc:
            logger.error(
                "[TTS] Primary %s continuous synthesis failed: %s",
                type(self.primary).__name__,
                exc,
            )
            result = False
        if result:
            self.last_provider = type(self.primary).__name__
            self._last_adapter = self.primary
            logger.info("[TTS] Provider used: %s", self.last_provider)
            return True
        if getattr(self.primary, "playback_started", False):
            self.last_provider = type(self.primary).__name__
            self._last_adapter = self.primary
            logger.error(
                "[TTS] Primary failed after playback began; fallback suppressed "
                "to avoid duplicate speech"
            )
            return False
        combined = " ".join(self._stream_segments).strip()
        if not combined:
            return False
        logger.warning(
            "[TTS] Primary produced no audio; switching to %s",
            type(self.fallback).__name__,
        )
        self.primary_ready = False
        result = bool(self.fallback.speak(combined, self._stream_language))
        self.last_provider = type(self.fallback).__name__
        self._last_adapter = self.fallback
        return result

    def abort_utterance(self) -> None:
        self._streaming_primary = False
        self._stream_segments = []
        try:
            self.primary.abort_utterance()
        except Exception as exc:
            logger.warning("[TTS] Could not abort primary utterance: %s", exc)

    def speak(self, text: str, language: str = "en") -> bool:
        if self.primary_ready:
            try:
                if self.primary.speak(text, language):
                    self.last_provider = type(self.primary).__name__
                    self._last_adapter = self.primary
                    logger.info("[TTS] Provider used: %s", self.last_provider)
                    return True
            except Exception as exc:
                logger.warning(
                    "[TTS] Primary %s exception: %s",
                    type(self.primary).__name__,
                    exc,
                )
            if getattr(self.primary, "playback_started", False):
                self.last_provider = type(self.primary).__name__
                self._last_adapter = self.primary
                logger.error(
                    "[TTS] Primary failed after playback began; fallback suppressed "
                    "to avoid duplicate speech"
                )
                return False
            logger.warning(
                "[TTS] Primary %s produced no audio; switching to %s",
                type(self.primary).__name__,
                type(self.fallback).__name__,
            )
            self.primary_ready = False
        try:
            result = self.fallback.speak(text, language)
            self.last_provider = type(self.fallback).__name__
            self._last_adapter = self.fallback
            log = logger.info if result else logger.error
            log(
                "[TTS] Fallback %s result: %s",
                self.last_provider,
                "audio played" if result else "no audio",
            )
            return result
        except Exception as exc:
            logger.error(
                "[TTS] Fallback %s failed: %s",
                type(self.fallback).__name__,
                exc,
            )
            raise

    def close(self) -> None:
        self.abort_utterance()
        self.primary.close()
        self.fallback.close()

    @property
    def last_first_audio_ms(self):
        return getattr(self._last_adapter, "last_first_audio_ms", None)

    @property
    def last_total_ms(self):
        return getattr(self._last_adapter, "last_total_ms", None)

    def provider_status(self) -> str:
        active = self.last_provider or "not used yet"
        return (
            f"{type(self.primary).__name__} primary "
            f"({'ready' if self.primary_ready else 'unavailable'}); "
            f"{type(self.fallback).__name__} fallback "
            f"({'ready' if self.fallback_ready else 'unavailable'}); "
            f"last={active}"
        )
