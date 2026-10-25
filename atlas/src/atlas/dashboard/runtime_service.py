"""RuntimeService: the dashboard's bridge into the ATLAS container.

Holds the teacher-facing session state (language, profile, pack, manual
artwork override) and exposes privacy-safe operations for the API layer.
All heavy components come from the existing dependency container — this
module never constructs its own pipeline.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from atlas.app.dependency_container import Container
from atlas.audio.devices import find_alsa_playback, find_pulse_playback
from atlas.audio.playback import join_output_device_names
from atlas.config.settings import Settings
from atlas.dashboard.activity import (
    explain_event,
    explain_runtime,
    pair_entries,
    safe_event,
    safe_runtime_line,
)
from atlas.dashboard.visitor_activation import (
    clean_greeting_name,
    local_greeting,
    session_introduction,
    wake_phrase_matches,
)
from atlas.dialogue.conversation_memory import interleave_context
from atlas.dialogue.scripted_faq import resolve_scripted_faq
from atlas.models.enums import EducationalLevel, Language, RunMode
from atlas.models.languages import OUTPUT_LANGUAGE_NAMES, normalize_language_code
from atlas.models.retrieval import RetrievalQuery
from atlas.utils.ids import new_session_id
from atlas.utils.time import Timer, now_iso

logger = logging.getLogger(__name__)

_DEFAULT_PROFILE = EducationalLevel.ADULT_BEGINNER.value


def _human_runtime_line(line: str) -> str:
    """Turn one process-log line into a readable operator update."""
    cleaned = re.sub(r"^\d{4}-\d{2}-\d{2}[^ ]*\s+\w+\s+[^:]+:\s+", "", line).strip()
    if "[STT live]" in cleaned:
        speech = re.sub(
            r"\s+\[language=[^\]]+\]$",
            "",
            cleaned.split("[STT live]", 1)[1].strip(),
        )
        return "Visitor is speaking: " + speech
    if "[STT final]" in cleaned:
        speech = re.sub(
            r"\s+\[language=[^\]]+\]$",
            "",
            cleaned.split("[STT final]", 1)[1].strip(),
        )
        return "Visitor said: " + speech
    if "[STT] Preparing to listen" in cleaned:
        language = re.search(r"language=([a-z-]+)", cleaned)
        timeout = re.search(r"timeout=([\d.]+s)", cleaned)
        language_code = (language.group(1) if language else "").split("-")[0]
        language_name = OUTPUT_LANGUAGE_NAMES.get(
            language_code, "the selected language"
        )
        timeout_text = timeout.group(1) if timeout else "the configured window"
        return f"ATLAS is listening in {language_name} for up to {timeout_text}."
    if "[Deepgram] Listening" in cleaned:
        return "Microphone opened with Deepgram and Silero voice detection."
    if "[Silero VAD] Speech started" in cleaned:
        return "Speech detected. ATLAS is recording the question."
    if "[STT] No transcript" in cleaned:
        return "No usable speech was received before listening ended."
    if "[STT] Provider used:" in cleaned:
        return "Speech recognition used " + cleaned.split(":", 1)[1].strip() + "."
    if "[STT]" in cleaned and (
        "failed" in cleaned.lower() or "unavailable" in cleaned.lower()
    ):
        detail = cleaned.split("[STT]", 1)[1].strip()
        return "Warning: speech recognition could not complete. " + detail
    if "[RAG] Retrieved" in cleaned:
        return "Knowledge search completed: " + cleaned.split("[RAG]", 1)[1].strip()
    if "[LLM final]" in cleaned:
        return "ATLAS answer: " + cleaned.split("[LLM final]", 1)[1].strip()
    if "[ATLAS final]" in cleaned:
        return "ATLAS answer: " + cleaned.split("[ATLAS final]", 1)[1].strip()
    if "[LLM sentence" in cleaned:
        return "ATLAS is saying: " + re.sub(r"^\[LLM sentence \d+\]\s*", "", cleaned)
    if "[Gemini]" in cleaned:
        return "Gemini: " + cleaned.split("[Gemini]", 1)[1].strip()
    if "[Cartesia] Continuous context opened" in cleaned:
        return "Cartesia locked one voice for this response."
    if "[Cartesia] First audio received" in cleaned:
        return "Cartesia began audible speech."
    if "[Cartesia] Continuous synthesis complete" in cleaned:
        return "Cartesia finished the response."
    if "[TTS] Response voice locked" in cleaned:
        detail = cleaned.split("locked", 1)[1].strip()
        return "Voice locked for this response. " + detail
    if "[LLM]" in cleaned:
        return "ATLAS is preparing an answer: " + cleaned.split("[LLM]", 1)[1].strip()
    if "[Cartesia] Continuous synthesis started" in cleaned:
        detail = cleaned.split("started", 1)[1].strip()
        return "ATLAS started speaking with Cartesia. " + detail
    if "[TTS] Continuous segment" in cleaned:
        return "Voice stream: " + cleaned.split("[TTS]", 1)[1].strip()
    if "[TTS]" in cleaned or "[Cartesia]" in cleaned:
        return "Voice: " + re.sub(r"^\[(TTS|Cartesia)\]\s*", "", cleaned)
    if "[Vision]" in cleaned:
        return "Vision: " + cleaned.split("[Vision]", 1)[1].strip()
    if "ERROR" in line or "WARNING" in line or "failed" in cleaned.lower():
        return "Warning: " + cleaned
    if "Camera" in cleaned:
        return "Camera: " + re.sub(r"^\[?Camera\]?\s*", "", cleaned)
    if "[Timing]" in cleaned:
        return "Timing: " + cleaned.split("[Timing]", 1)[1].strip()
    return cleaned


def _human_event(event: dict[str, Any]) -> dict[str, Any]:
    """Summarize one structured event without raw log formatting."""
    name = str(event.get("event") or "event").replace("_", " ")
    state = str(event.get("state") or "system")
    details = [
        f"{key.replace('_', ' ')}: {value}"
        for key, value in sorted(event.items())
        if key not in {"event_id", "session_id", "timestamp", "state", "event"}
    ]
    return {
        "timestamp": event.get("timestamp", ""),
        "summary": f"{state.title()}: {name}.",
        "details": "; ".join(details) or "No additional fields.",
    }


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _to_language(value: str | None, fallback: str = "en") -> Language:
    return Language(normalize_language_code(value, fallback))


def _to_level(value: str | None) -> EducationalLevel:
    try:
        return EducationalLevel(str(value).lower())
    except (ValueError, TypeError):
        return EducationalLevel.ADULT_BEGINNER


class RuntimeService:
    def __init__(
        self,
        container: Container,
        capture_request: Callable[[], None] | None = None,
        session_changed: Callable[[], None] | None = None,
    ) -> None:
        self.container = container
        self._capture_request = capture_request
        self._session_changed = session_changed
        self._session_lock = threading.RLock()
        self._session_generation = 0
        self.session_id: str | None = None
        self.language: str = "en"
        self.profile: str = _DEFAULT_PROFILE
        self.pack_id: str = container.settings.default_pack_id
        self.accessibility_mode: bool = False
        self.demo_active: bool = False
        self._visitor_interests: list[str] = []
        self._visitor_accessibility: list[str] = []
        self._visitor_expertise: str | None = None
        self._wake_required = False
        self._wake_activated = True
        self._greeting_name: str | None = None
        self._greeting_pending = False
        hardware = container.settings.hardware
        configured_output = str(hardware.audio_output_name).strip()
        self._headset_output_name = str(hardware.headset_name).strip()
        self._speaker_output_name = (
            configured_output
            if configured_output and configured_output != self._headset_output_name
            else str(hardware.judge_speaker_name).strip()
        )
        self.audio_route = (
            "speaker"
            if configured_output and configured_output != self._headset_output_name
            else "headset"
        )
        self.audio_volume_percent = int(hardware.audio_volume_percent)
        self.last_answer: dict[str, Any] | None = None
        self._last_interaction: dict[str, Any] | None = None
        self._pending_settings: Settings | None = None
        # Demo-only simulation flags (never active outside dev/demo mode).
        self.demo_flags: set[str] = set()

    # -- session -----------------------------------------------------------
    def start_session(
        self,
        *,
        demo: bool = False,
        wake_required: bool = False,
        greeting_name: str | None = None,
    ) -> dict[str, Any]:
        with self._session_lock:
            self._invalidate_session()
            return self._start_session(
                demo=demo, wake_required=wake_required, greeting_name=greeting_name
            )

    def _invalidate_session(self) -> None:
        self._session_generation += 1
        self.last_answer = None
        self._last_interaction = None
        self.container.artwork_tracker.reset()
        self.container.dialogue_engine.reset_conversation()
        if self._session_changed is not None:
            self._session_changed()

    def _start_session(
        self, *, demo: bool, wake_required: bool, greeting_name: str | None
    ) -> dict[str, Any]:
        configure = getattr(
            self.container.dialogue_engine,
            "configure_personalization",
            None,
        )
        if callable(configure):
            configure(
                interests=self._visitor_interests,
                accessibility=self._visitor_accessibility,
                expertise=self._visitor_expertise,
            )
        self.demo_active = bool(demo)
        self._wake_required = bool(wake_required)
        self._wake_activated = not self._wake_required
        self._greeting_name = clean_greeting_name(greeting_name)
        self._greeting_pending = not self._wake_required
        self.session_id = new_session_id()
        self.container.logger.log(
            session_id=self.session_id,
            state="session",
            event=(
                "visitor_start_waiting_for_wake"
                if self._wake_required
                else ("demo_start" if self.demo_active else "session_start")
            ),
        )
        return {
            "session_id": self.session_id,
            "demo_active": self.demo_active,
            "activation_state": (
                "waiting_for_wake" if self._wake_required else "active"
            ),
        }

    def stop_session(self) -> dict[str, Any]:
        with self._session_lock:
            self._invalidate_session()
            return self._stop_session()

    def _stop_session(self) -> dict[str, Any]:
        if self.session_id:
            self.container.logger.log(
                session_id=self.session_id, state="session", event="session_stop"
            )
        stopped = self.session_id
        self.session_id = None
        self.demo_active = False
        self._wake_required = False
        self._wake_activated = True
        self._greeting_name = None
        self._greeting_pending = False
        self._visitor_interests = []
        self._visitor_accessibility = []
        self._visitor_expertise = None
        return {"stopped_session_id": stopped, "demo_active": False}

    def set_profile(
        self,
        language: str | None = None,
        profile: str | None = None,
        pack_id: str | None = None,
        accessibility_mode: bool | None = None,
        interests: list[str] | None = None,
        accessibility: list[str] | None = None,
        expertise: str | None = None,
    ) -> dict[str, Any]:
        if language is not None:
            self.language = _to_language(language).value
        if profile is not None:
            self.profile = _to_level(profile).value
        if pack_id is not None:
            self.pack_id = pack_id
        if accessibility_mode is not None:
            self.accessibility_mode = bool(accessibility_mode)
            if self.accessibility_mode and profile is None:
                self.profile = EducationalLevel.VISUAL_IMPAIRMENT.value
        if interests is not None:
            self._visitor_interests = list(interests)
        if accessibility is not None:
            self._visitor_accessibility = list(accessibility)
        if expertise is not None:
            self._visitor_expertise = expertise
        return self.experience_settings()

    @property
    def wake_pending(self) -> bool:
        return bool(
            self.session_id and self._wake_required and not self._wake_activated
        )

    @property
    def visitor_accessibility(self) -> tuple[str, ...]:
        """Return privacy-bounded accessibility choices for the live runner."""
        return tuple(self._visitor_accessibility)

    def speak_pending_greeting(self) -> bool:
        """Consume one new-session greeting on the device runtime thread.

        HTTP session-start handlers only queue it; they never synthesize or
        block on audio. Claim and erase the optional name before synthesis,
        prevent duplicate greetings, and never retry a partial spoken greeting.
        The session-change callback aborts playback if staff stop or restart.
        """
        with self._session_lock:
            if not self.session_id or not self._greeting_pending:
                return False
            self._greeting_pending = False
            name = self._greeting_name
            self._greeting_name = None
            generation = self._session_generation
            language = self.language
            if bool(getattr(self.container.hardware, "emergency_stopped", False)):
                return False
        introduction = session_introduction(language, name)
        with self._session_lock:
            if generation != self._session_generation or self.session_id is None:
                return False
        try:
            if name:
                spoken = bool(
                    self.container.tts.speak_private_local(introduction, language)
                )
            else:
                spoken = bool(self.container.tts.speak(introduction, language))
        except Exception:
            # Provider exceptions may contain request text; never log their
            # traceback because the named version is private local-only data.
            logger.warning("[Activation] Session introduction audio failed")
            return False
        with self._session_lock:
            if generation != self._session_generation:
                return False
        logger.info(
            "[Activation] Session introduction completed "
            "[language=%s audio_played=%s]", language, spoken,
        )
        return spoken

    def activate_from_wake(self, transcript: str) -> bool:
        """Accept the local wake phrase and play a private local greeting."""
        if not self.wake_pending:
            return True
        if not wake_phrase_matches(transcript, self.language):
            return False
        name = self._greeting_name
        generation = self._session_generation
        greeting = local_greeting(self.language, name)
        if name:
            spoken = bool(
                self.container.tts.speak_private_local(greeting, self.language)
            )
        else:
            spoken = bool(self.container.tts.speak(greeting, self.language))
        if name and not spoken:
            logger.error(
                "[Activation] Private local greeting failed; wake gate remains active"
            )
            return False
        with self._session_lock:
            if generation != self._session_generation:
                return False
            self._wake_activated = True
            self._greeting_name = None
        logger.info(
            "[Activation] Wake phrase accepted; local greeting completed "
            "[language=%s audio_played=%s]",
            self.language,
            spoken,
        )
        return True

    def private_local_speech_ready(self, language: str | None = None) -> bool:
        """Report whether a name can be spoken without any cloud provider."""
        selected = _to_language(language or self.language).value
        return bool(self.container.tts.supports_private_language(selected))

    def experience_settings(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "profile": self.profile,
            "pack_id": self.pack_id,
            "accessibility_mode": self.accessibility_mode,
        }

    # -- live audio routing -------------------------------------------------
    def _audio_output_name(self, route: str) -> str:
        if route == "headset":
            return self._headset_output_name
        if route == "speaker" and self._speaker_output_name:
            return self._speaker_output_name
        if route == "both" and self._headset_output_name and self._speaker_output_name:
            return join_output_device_names(
                self._headset_output_name, self._speaker_output_name
            )
        raise ValueError("judge speaker name is not configured")

    def _audio_output_names(self, route: str) -> tuple[str, ...]:
        if route == "both":
            return tuple(
                name
                for name in (self._headset_output_name, self._speaker_output_name)
                if name
            )
        return (self._audio_output_name(route),)

    @staticmethod
    def _audio_device_available(output_name: str) -> bool:
        return bool(find_pulse_playback(output_name) or find_alsa_playback(output_name))

    def audio_status(self) -> dict[str, Any]:
        active_names = self._audio_output_names(self.audio_route)
        active_name = " + ".join(active_names) or "Unconfigured"
        tts = self.container.tts
        provider_status = getattr(tts, "provider_status", None)
        return {
            "route": self.audio_route,
            "volume_percent": self.audio_volume_percent,
            "output_device_name": active_name,
            "headset_name": self._headset_output_name,
            "speaker_name": self._speaker_output_name,
            "headset_available": self._audio_device_available(
                self._headset_output_name
            ),
            "speaker_available": bool(
                self._speaker_output_name
                and self._audio_device_available(self._speaker_output_name)
            ),
            "both_available": all(
                bool(name) and self._audio_device_available(name)
                for name in (self._headset_output_name, self._speaker_output_name)
            ),
            "microphone_route": "headset",
            "provider": (
                provider_status() if callable(provider_status) else type(tts).__name__
            ),
        }

    def set_audio_output(
        self,
        *,
        route: str | None = None,
        volume_percent: int | None = None,
    ) -> dict[str, Any]:
        next_route = route or self.audio_route
        next_volume = (
            self.audio_volume_percent
            if volume_percent is None
            else min(100, max(0, int(volume_percent)))
        )
        output_names = self._audio_output_names(next_route)
        output_name = self._audio_output_name(next_route)
        if self.container.settings.mode == RunMode.DEVICE and not all(
            self._audio_device_available(name) for name in output_names
        ):
            unavailable = [
                name for name in output_names if not self._audio_device_available(name)
            ]
            raise LookupError(f"audio output is unavailable: {', '.join(unavailable)}")
        tts = self.container.tts
        tts.set_output_device(output_name)
        tts.set_volume(next_volume)
        self.audio_route = next_route
        self.audio_volume_percent = next_volume
        logger.info(
            "[Audio] Output changed [route=%s device=%s volume=%d%%]",
            self.audio_route,
            output_name,
            self.audio_volume_percent,
        )
        return self.audio_status()

    def test_audio_output(self) -> dict[str, Any]:
        played = bool(self.container.tts.test_sound())
        if not played:
            raise RuntimeError("test sound did not reach the selected output")
        logger.info(
            "[Audio] Test sound played [route=%s volume=%d%%]",
            self.audio_route,
            self.audio_volume_percent,
        )
        return {"played": True, "audio": self.audio_status()}

    # -- artwork context -----------------------------------------------------
    def set_manual_artwork(self, artwork_id: str) -> dict[str, Any]:
        known = self._artwork_map()
        if known and artwork_id not in known:
            raise ValueError(f"unknown artwork_id: {artwork_id}")
        with self._session_lock:
            self.container.artwork_tracker.set_manual_override(
                artwork_id, label=known.get(artwork_id)
            )
            self.container.dialogue_engine.prepare_turn(
                "", artwork_id, force_camera=True
            )
        return self.container.artwork_tracker.status()

    def clear_manual_artwork(self) -> dict[str, Any]:
        self.container.artwork_tracker.clear_manual_override()
        return self.container.artwork_tracker.status()

    def capture_artwork(self) -> dict[str, Any]:
        """Identify the center crop without storing the source frame."""
        if self._capture_request is not None:
            self._capture_request()
            return {"requested": True, "capture_source": "device_runtime"}

        with self._session_lock:
            generation = self._session_generation
            engine = self.container.dialogue_engine
            engine_generation = engine.conversation_generation

        capture = self.container.manual_artwork_capture
        if capture is None:
            raise RuntimeError(
                "manual capture requires device/demo mode with Gemini enabled"
            )
        camera = self.container.camera_source
        camera.start(timeout_s=5.0)
        frame, _ = camera.latest(copy=True)
        if frame is None:
            raise RuntimeError("camera has no current frame")
        detection = capture.identify(frame)
        if detection is None:
            raise LookupError("the centered artwork was not recognized")
        with self._session_lock:
            if (
                generation != self._session_generation
                or engine_generation != engine.conversation_generation
            ):
                raise RuntimeError(
                    "Session changed while identifying; capture cancelled"
                )
            self.container.artwork_tracker.set_manual_override(
                detection.artwork_id, detection.label
            )
            engine.prepare_turn(
                "",
                detection.artwork_id,
                expected_generation=engine_generation,
                force_camera=True,
            )
        status = self.container.artwork_tracker.status()
        status["capture_source"] = "manual_center_crop"
        return status

    def artwork_status(self) -> dict[str, Any]:
        status = self.container.artwork_tracker.status()
        # Preserve the legacy selected/last-stable subject, but distinguish it
        # from an actual current view. Camera loss must not erase discussion
        # memory or make a typed question claim to see a remembered painting.
        visual = self.container.artwork_tracker.visualization_status()
        try:
            camera_ready = bool(self.container.camera_source.status().get("ready"))
        except Exception:
            camera_ready = False
        live_id = (
            visual.get("artwork_id")
            if visual.get("stable") and (
                status.get("manual_override") or camera_ready
            ) else None
        )
        status["live_artwork_id"] = live_id
        status["current_view_confirmed"] = live_id is not None
        if "low_confidence" in self.demo_flags:
            status["confidence"] = 0.30
            status["stable"] = False
            status["warning"] = "low_confidence (simulated)"
        return status

    def camera_frame_jpeg(self) -> bytes:
        """Return one annotated in-memory frame without storing it."""
        import cv2

        frame, _ = self.container.camera_source.latest(copy=True)
        if frame is None:
            raise RuntimeError("camera has no current frame")

        visual = self.container.artwork_tracker.visualization_status()
        bbox = visual.get("bbox")
        if bbox:
            height, width = frame.shape[:2]
            x1, y1, x2, y2 = (
                int(bbox[0] * width),
                int(bbox[1] * height),
                int(bbox[2] * width),
                int(bbox[3] * height),
            )
            color = (45, 190, 135) if visual.get("stable") else (235, 170, 45)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
            confidence = visual.get("confidence")
            confidence_text = (
                f" {confidence * 100:.0f}%" if confidence is not None else ""
            )
            label = f"{visual.get('label') or 'Artwork'}{confidence_text}"
            text_y = max(28, y1 - 10)
            cv2.putText(
                frame,
                label,
                (max(8, x1), text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
                cv2.LINE_AA,
            )

        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not ok:
            raise RuntimeError("camera frame encoding failed")
        return encoded.tobytes()

    def arducam_status(self) -> dict[str, Any]:
        """Return privacy-safe state for the independent CSI admin preview."""
        hardware = self.container.settings.hardware
        configured = {
            "enabled": hardware.arducam_enabled,
            "sensor_id": hardware.arducam_sensor_id,
            "configured_width": hardware.arducam_width,
            "configured_height": hardware.arducam_height,
            "configured_fps": hardware.arducam_fps,
            "flip_method": hardware.arducam_flip_method,
        }
        if not hardware.arducam_enabled:
            return {
                **configured,
                "ready": False,
                "last_error": "Arducam preview is disabled in settings",
                "observed_fps": 0.0,
                "reconnect_count": 0,
            }

        source = self.container.arducam_source
        try:
            source.start(timeout_s=0.75)
        except RuntimeError as exc:
            logger.debug("Arducam preview is not ready yet: %s", exc)
        status = source.status()
        status["source"] = "Jetson CSI / nvarguscamerasrc"
        if status.get("last_error"):
            status["operator_message"] = (
                f"Argus sensor {hardware.arducam_sensor_id} produced no frame. "
                "Restart nvargus-daemon or cold power-cycle, then reseat the "
                "ribbon if the direct V4L2 test still times out."
            )
        return {**status, **configured}

    def arducam_frame_jpeg(self) -> bytes:
        """Return one IMX477 frame without persisting or passing it to YOLO."""
        import cv2

        hardware = self.container.settings.hardware
        if not hardware.arducam_enabled:
            raise RuntimeError("Arducam preview is disabled in settings")
        source = self.container.arducam_source
        source.start(timeout_s=2.0)
        frame, _ = source.latest(copy=True)
        if frame is None:
            raise RuntimeError("Arducam has no current frame")
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not ok:
            raise RuntimeError("Arducam frame encoding failed")
        return encoded.tobytes()

    def _artwork_map(self) -> dict[str, str]:
        """artwork_id -> title for the selected pack."""
        from atlas.rag.ingest import load_content_pack

        pack_dir = Path(self.container.settings.paths.content_packs_dir) / self.pack_id
        if not (pack_dir / "manifest.json").exists():
            return {}
        try:
            pack = load_content_pack(pack_dir)
        except Exception:
            return {}
        return {a.artwork_id: a.title for a in pack.artworks}

    # -- typed-question fallback ----------------------------------------------
    def record_voice_result(
        self, result: Any, *, session_id: str, expected_generation: int,
        latency_ms: float,
    ) -> bool:
        """Project only outcome flags, never retain speech, prompts or answers."""
        with self._session_lock:
            if (
                self.session_id != session_id
                or expected_generation
                != self.container.dialogue_engine.conversation_generation
                or getattr(result, "error", None) == "session_cancelled"
            ):
                return False
            dialogue = getattr(result, "dialogue", None)
            response_failed = bool(
                getattr(result, "error", None) or getattr(dialogue, "error", None)
            )
            speech_ok = bool(getattr(result, "tts_ok", True))
            self._last_interaction = {
                "source": "voice",
                "state": (
                    "failed" if response_failed or not speech_ok
                    else "completed" if dialogue is not None else "control"
                ),
                "response_failed": response_failed,
                "speech_ok": speech_ok,
                "fallback_used": bool(getattr(dialogue, "fallback_used", False)),
                "latency_ms": (
                    max(0.0, latency_ms) if math.isfinite(latency_ms) else None
                ),
            }
            return True

    def ask(
        self,
        question: str,
        language: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        with self._session_lock:
            generation = self._session_generation
            engine_generation = self.container.dialogue_engine.conversation_generation
            session_id = self.session_id or "no_session"
        answer = self._answer_question(
            question, language, profile, engine_generation, session_id
        )
        with self._session_lock:
            if (
                generation != self._session_generation
                or answer.get("error") == "session_cancelled"
            ):
                raise RuntimeError(
                    "Session changed while answering; question cancelled"
                )
            self.last_answer = answer
            self._last_interaction = {
                "source": "dashboard",
                "state": "failed" if answer.get("error") else "completed",
                "response_failed": bool(answer.get("error")),
                "speech_ok": None,
                "fallback_used": bool(answer.get("fallback_used")),
                "latency_ms": answer.get("total_latency_ms"),
            }
        return answer

    def _answer_question(
        self,
        question: str,
        language: str | None,
        profile: str | None,
        engine_generation: int,
        session_id: str,
    ) -> dict[str, Any]:
        lang = _to_language(language or self.language)
        level = _to_level(profile or self.profile)
        settings = self.container.settings
        if settings.logging.log_transcripts:
            logger.info("[Typed question] %s", question)
        artwork = self.artwork_status()
        artwork_id = artwork.get("live_artwork_id")
        engine = self.container.dialogue_engine
        focus = engine.prepare_turn(
            question, artwork_id, expected_generation=engine_generation
        )
        if focus is None:
            return {"error": "session_cancelled"}
        retrieval_id = focus.retrieval_artwork_id

        with Timer() as scripted_timer:
            scripted = resolve_scripted_faq(
                question,
                artwork_id=retrieval_id,
                language=lang.value,
                profile=level.value,
                accessibility=self._visitor_accessibility,
                resolved_subject=True,
            )
        if scripted is not None:
            remember = getattr(
                self.container.dialogue_engine,
                "remember_local_response",
                None,
            )
            if callable(remember):
                remember(
                    question,
                    scripted.response,
                    expected_generation=engine_generation,
                    focus=focus,
                )
            answer = {
                "answer": scripted.response,
                "language": lang.value,
                "grounded": True,
                "fallback_used": False,
                "filtered": False,
                "confidence": "high",
                "used_chunk_ids": list(scripted.source_ids),
                "artwork_id": scripted.artwork_id,
                "retrieval_latency_ms": 0.0,
                "total_latency_ms": scripted_timer.elapsed_ms,
                "error": None,
            }
            logger.info(
                "[Timing] Scripted FAQ %.2f ms [intent=%s artwork_id=%s]",
                scripted_timer.elapsed_ms,
                scripted.intent,
                scripted.artwork_id or "none",
            )
            if settings.logging.log_llm_responses:
                logger.info("[ATLAS final] %s", scripted.response)
            # Keep the pre-existing FAQ question privacy behaviour: no new
            # visitor text is persisted just to populate the readable view.
            try:
                self.container.logger.log(
                    session_id=session_id, state="dashboard", event="typed_question",
                    language=lang.value, artwork_id=scripted.artwork_id,
                )
            except Exception as exc:
                logger.warning(
                    "Dashboard activity could not be recorded: %s", type(exc).__name__,
                )
            return answer

        if "llm_timeout" in self.demo_flags:
            timeout_fallbacks = {
                Language.EN: "I'm sorry, I can't generate a response right now.",
                Language.FR: "Je suis désolé, je ne peux pas répondre en ce moment.",
                Language.ES: (
                    "Lo siento, no puedo generar una respuesta en este momento."
                ),
                Language.IT: (
                    "Mi dispiace, non posso generare una respuesta in questo momento."
                ),
                Language.ZH: "抱歉，我現在無法產生回應。",
            }
            fallback = timeout_fallbacks[lang]
            return {
                "answer": fallback,
                "language": lang.value,
                "grounded": False,
                "fallback_used": True,
                "filtered": False,
                "confidence": "low",
                "used_chunk_ids": [],
                "artwork_id": artwork_id,
                "retrieval_latency_ms": None,
                "total_latency_ms": None,
                "error": "simulated_llm_timeout",
            }

        with Timer() as total:
            groups = []
            retrieval_latency_ms = 0.0
            for identifier in focus.retrieval_artwork_ids:
                result = self.container.retriever.retrieve(
                    RetrievalQuery(
                        text=question,
                        artwork_id=identifier,
                        language=lang,
                        educational_level=level,
                    )
                )
                groups.append(
                    [{"text": c.text, "chunk_id": c.chunk_id} for c in result.chunks]
                )
                retrieval_latency_ms += result.total_latency_ms or 0.0
            chunks = interleave_context(groups)
            dialogue = self.container.dialogue_engine.respond(
                question=question,
                artwork_chunks=chunks,
                language=lang.value,
                profile=level.value,
                artwork_id=artwork_id,
                expected_generation=engine_generation,
                focus=focus,
            )

        answer = {
            "answer": dialogue.response,
            "language": dialogue.language,
            "grounded": dialogue.grounded,
            "fallback_used": dialogue.fallback_used,
            "filtered": dialogue.filtered,
            "confidence": dialogue.confidence,
            "used_chunk_ids": dialogue.used_chunk_ids,
            "artwork_id": focus.artwork_id,
            "retrieval_latency_ms": retrieval_latency_ms,
            "total_latency_ms": total.elapsed_ms,
            "error": dialogue.error,
        }
        if (
            dialogue.error == "session_cancelled"
            or engine_generation
            != self.container.dialogue_engine.conversation_generation
        ):
            raise RuntimeError("Session changed while answering; question cancelled")
        if settings.logging.log_llm_responses:
            logger.info("[LLM final] %s", dialogue.response)
        logger.info(
            "[Timing] Typed question total %.0f ms "
            "[retrieval_ms=%s grounded=%s fallback=%s error=%s]",
            total.elapsed_ms,
            (
                f"{retrieval_latency_ms:.0f}"
                if retrieval_latency_ms is not None
                else "n/a"
            ),
            dialogue.grounded,
            dialogue.fallback_used,
            dialogue.error or "none",
        )

        log_fields: dict[str, Any] = {
            "language": lang.value,
            "artwork_id": artwork_id,
            "retrieval_latency_ms": retrieval_latency_ms,
            "fallback_used": dialogue.fallback_used,
        }
        if settings.logging.log_transcripts:
            transcript = question
            if settings.privacy.transcript_logging_sanitized:
                transcript = transcript[:200]
            log_fields["transcript"] = transcript
        try:
            self.container.logger.log(
                session_id=session_id,
                state="dashboard",
                event="typed_question",
                **log_fields,
            )
        except Exception as exc:
            # Activity is advisory, just as for the local FAQ path above.
            logger.warning(
                "Dashboard activity could not be recorded: %s", type(exc).__name__,
            )
        return answer

    # -- content ---------------------------------------------------------------
    def content_packs(self) -> list[dict[str, Any]]:
        packs_dir = Path(self.container.settings.paths.content_packs_dir)
        out: list[dict[str, Any]] = []
        if not packs_dir.exists():
            return out
        for pack_dir in sorted(packs_dir.iterdir()):
            manifest = pack_dir / "manifest.json"
            if not manifest.is_file():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            out.append(
                {
                    "pack_id": data.get("pack_id", pack_dir.name),
                    "name": data.get("name", pack_dir.name),
                    "languages": data.get("languages", []),
                    "selected": pack_dir.name == self.pack_id,
                }
            )
        return out

    def artworks(self) -> list[dict[str, str]]:
        return [
            {"artwork_id": aid, "title": title}
            for aid, title in sorted(self._artwork_map().items())
        ]

    def ingest_pack(self, pack_id: str, reset: bool = True) -> dict[str, Any]:
        from atlas.rag.ingest import ingest_pack

        pack_dir = Path(self.container.settings.paths.content_packs_dir) / pack_id
        if not (pack_dir / "manifest.json").exists():
            raise ValueError(f"no manifest.json for pack: {pack_id}")
        return ingest_pack(self.container.settings, pack_dir, reset=reset)

    def run_rag_eval(self) -> dict[str, Any]:
        from atlas.rag.evaluator import DEMO_EVAL_CASES, evaluate_by_category

        reports = evaluate_by_category(self.container.retriever, DEMO_EVAL_CASES)
        return {
            cat: {"n": rep.n, "hit_rate_at_k": rep.hit_rate_at_k, "mrr": rep.mrr}
            for cat, rep in sorted(reports.items())
        }

    # -- operator configuration ----------------------------------------------
    @staticmethod
    def _editable_config(settings: Settings) -> dict[str, Any]:
        llm = settings.llm
        speech = settings.speech
        hardware = settings.hardware
        rag = settings.rag
        logging_settings = settings.logging
        return {
            "llm": {
                "provider": llm.provider,
                "model": llm.model,
                "cloud_llm_enabled": llm.cloud_llm_enabled,
                "streaming_enabled": llm.streaming_enabled,
                "sentence_tts_enabled": llm.sentence_tts_enabled,
                "timeout_s": llm.timeout_s,
            },
            "speech": {
                "stt_provider": speech.stt_provider,
                "tts_provider": speech.tts_provider,
                "cloud_speech_enabled": speech.cloud_speech_enabled,
                "offline_fallback_enabled": speech.offline_fallback_enabled,
                "deepgram_model": speech.deepgram_model,
                "deepgram_language": speech.deepgram_language,
                "listen_duration_s": speech.listen_duration_s,
                "max_utterance_s": speech.max_utterance_s,
                "silero_threshold": speech.silero_threshold,
                "silero_min_silence_ms": speech.silero_min_silence_ms,
                "silero_hesitation_silence_ms": speech.silero_hesitation_silence_ms,
                "cartesia_model": speech.cartesia_model,
                "cartesia_voice_id": speech.cartesia_voice_id,
            },
            "hardware": {
                "yolo_backend": hardware.yolo_backend,
                "camera_width": hardware.camera_width,
                "camera_height": hardware.camera_height,
                "camera_fps": hardware.camera_fps,
                "camera_reconnect_s": hardware.camera_reconnect_s,
                "vision_conf_threshold": hardware.vision_conf_threshold,
                "vision_mask_conf_threshold": hardware.vision_mask_conf_threshold,
                "vision_center_weight": hardware.vision_center_weight,
                "vision_center_threshold": hardware.vision_center_threshold,
                "vision_hold_seconds": hardware.vision_hold_seconds,
                "vision_gap_tolerance_s": hardware.vision_gap_tolerance_s,
                "manual_capture_crop_ratio": hardware.manual_capture_crop_ratio,
            },
            "rag": {
                "top_k": rag.top_k,
                "dense_top_k": rag.dense_top_k,
                "keyword_top_k": rag.keyword_top_k,
                "chunk_max_words": rag.chunk_max_words,
                "language_fallback_enabled": rag.language_fallback_enabled,
                "fallback_language": rag.fallback_language,
            },
            "logging": {
                "log_transcripts": logging_settings.log_transcripts,
                "log_live_stt": logging_settings.log_live_stt,
                "log_llm_responses": logging_settings.log_llm_responses,
            },
        }

    def dashboard_config(self) -> dict[str, Any]:
        settings = self._pending_settings or self.container.settings
        return {
            "config": self._editable_config(settings),
            "restart_required": self._pending_settings is not None,
        }

    def save_dashboard_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        """Validate and atomically persist a non-secret settings patch."""
        if not patch:
            return self.dashboard_config()

        current = self._pending_settings or self.container.settings
        candidate_data = _deep_merge(current.model_dump(mode="python"), patch)
        candidate = Settings.model_validate(candidate_data)

        override_path = Path(
            self.container.settings.dashboard.config_override_path
        ).expanduser()
        existing: dict[str, Any] = {}
        if override_path.exists():
            loaded = yaml.safe_load(override_path.read_text(encoding="utf-8")) or {}
            if not isinstance(loaded, dict):
                raise ValueError("dashboard override file must contain a mapping")
            existing = loaded
        persisted = _deep_merge(existing, patch)

        override_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = override_path.with_suffix(override_path.suffix + ".tmp")
        temporary.write_text(
            yaml.safe_dump(persisted, sort_keys=True), encoding="utf-8"
        )
        temporary.replace(override_path)
        self._pending_settings = candidate

        self.container.logger.log(
            session_id=self.session_id or "no_session",
            state="dashboard",
            event="settings_updated",
            extra={"changed_sections": ",".join(sorted(patch))},
        )
        return self.dashboard_config()

    # -- hardware ---------------------------------------------------------------
    def camera_pan_status(self) -> dict[str, Any]:
        return self.container.camera_pan.status()

    def camera_pan_control(self, req) -> dict[str, Any]:
        return self.container.camera_pan.command(
            req.action, client_id=str(req.client_id), sequence=req.sequence,
            control_epoch=str(req.control_epoch),
            angle=req.angle, direction=req.direction,
        )

    def emergency_stop(self) -> dict[str, Any]:
        # Pan must stop even if the independent exhibit stop fails.
        pan = getattr(self.container, "camera_pan", None)
        if pan is not None:
            pan.emergency_stop()
        self.container.hardware.emergency_stop()
        return {"emergency_stopped": True}

    def clear_emergency_stop(self) -> dict[str, Any]:
        self.container.hardware.clear_emergency_stop()
        pan = getattr(self.container, "camera_pan", None)
        if pan is not None:
            pan.clear_emergency_stop()
        return {"emergency_stopped": False}

    # -- demo controls -------------------------------------------------------
    def demo_simulate(self, scenario: str) -> dict[str, Any]:
        mode = self.container.settings.mode
        allow_device_testing = (
            self.container.settings.dashboard.allow_demo_controls
            and self.container.settings.dashboard.host
            in {"127.0.0.1", "localhost", "::1"}
        )
        if mode not in (RunMode.DEV, RunMode.DEMO) and not allow_device_testing:
            raise PermissionError("demo controls are only available in dev/demo mode")
        if scenario == "reset":
            self.demo_flags.clear()
            self.container.artwork_tracker.clear_manual_override()
        elif scenario.startswith("artwork:"):
            self.set_manual_artwork(scenario.split(":", 1)[1])
        elif scenario in ("low_confidence", "llm_timeout", "tts_failure"):
            self.demo_flags.add(scenario)
        else:
            raise ValueError(f"unknown scenario: {scenario}")
        return {"demo_flags": sorted(self.demo_flags), "scenario": scenario}

    # -- health / status / logs --------------------------------------------------
    def health(self) -> dict[str, Any]:
        c = self.container
        components: dict[str, str] = {}
        try:
            components["vector_store"] = "ok" if c.vector_store.count() > 0 else "empty"
        except Exception as exc:
            components["vector_store"] = f"error: {type(exc).__name__}"
        try:
            fts = c.fts_store
            components["fts_store"] = (
                "ok (fts5)" if getattr(fts, "has_fts", False) else "ok (bm25 fallback)"
            )
        except Exception as exc:
            components["fts_store"] = f"error: {type(exc).__name__}"
        try:
            components["retriever"] = type(c.retriever).__name__
            components["llm"] = type(c.dialogue_engine._llm).__name__
            stt_status = getattr(c.stt, "provider_status", None)
            tts_status = getattr(c.tts, "provider_status", None)
            components["stt"] = (
                stt_status() if callable(stt_status) else type(c.stt).__name__
            )
            components["tts"] = (
                tts_status() if callable(tts_status) else type(c.tts).__name__
            )
            components["vision"] = type(c.vision_detector).__name__
            components["hardware"] = type(c.hardware).__name__
        except Exception as exc:
            components["container"] = f"error: {type(exc).__name__}"
        return {
            "status": "ok",
            "mode": c.settings.mode.value,
            "components": components,
            "emergency_stopped": bool(getattr(c.hardware, "emergency_stopped", False)),
        }

    def status(self) -> dict[str, Any]:
        with self._session_lock:
            interaction = (
                dict(self._last_interaction) if self._last_interaction else None
            )
        settings = self.container.settings
        try:
            camera_status = self.container.camera_source.status()
        except Exception as exc:
            camera_status = {
                "ready": False,
                "last_frame_age_s": None,
                "last_error": f"{type(exc).__name__}: {exc}",
            }
        pan = getattr(self.container, "camera_pan", None)
        pan_status = pan.status() if pan is not None else None
        last = None
        if self.last_answer:
            last = {
                "answer": self.last_answer["answer"],
                "fallback_used": self.last_answer["fallback_used"],
                "grounded": self.last_answer["grounded"],
                "latency_ms": self.last_answer["total_latency_ms"],
            }
        return {
            "mode": settings.mode.value,
            "session_id": self.session_id,
            "session_active": self.session_id is not None,
            "demo_active": self.demo_active,
            "activation_state": (
                "idle"
                if self.session_id is None
                else ("waiting_for_wake" if self.wake_pending else "active")
            ),
            "experience": self.experience_settings(),
            "artwork": self.artwork_status(),
            "camera": camera_status,
            "camera_pan": pan_status,
            "last_answer": last,
            "last_interaction": interaction,
            "demo_flags": sorted(self.demo_flags),
            "privacy": {
                "store_raw_audio": settings.privacy.store_raw_audio,
                "store_raw_images": settings.privacy.store_raw_images,
                "store_face_data": settings.privacy.store_face_data,
                "anonymous_session_ids": settings.privacy.anonymous_session_ids,
                "transcript_logging": settings.logging.log_transcripts,
                "live_stt_logging": settings.logging.log_live_stt,
                "llm_response_logging": settings.logging.log_llm_responses,
                "cloud_llm_enabled": settings.llm.cloud_llm_enabled,
                "cloud_llm_provider": settings.llm.provider,
            },
            "emergency_stopped": bool(
                getattr(self.container.hardware, "emergency_stopped", False)
            ),
        }

    def recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.container.logger.read_recent(limit=limit)

    def human_recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        return [_human_event(event) for event in self.recent_logs(limit=limit)]

    def runtime_logs(self, limit: int = 250) -> dict[str, Any]:
        """Return the testing-mode tail of the device process log."""
        path = Path(self.container.settings.paths.logs_dir) / "atlas-runtime.log"
        if not path.is_file():
            return {
                "available": False,
                "lines": ["Runtime log will appear after ATLAS restarts."],
            }
        ansi = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
        try:
            with path.open("rb") as handle:
                handle.seek(0, 2)
                size = handle.tell()
                read_size = min(size, max(65536, min(limit * 512, 4 * 1024 * 1024)))
                handle.seek(size - read_size)
                raw = handle.read()
        except OSError as exc:
            return {
                "available": False,
                "lines": [f"Runtime log unavailable: {type(exc).__name__}"],
            }
        lines = raw.decode("utf-8", errors="replace").splitlines()
        if read_size < size and lines:
            lines = lines[1:]
        return {
            "available": True,
            "lines": [ansi.sub("", line.rstrip()) for line in lines[-limit:]],
        }

    def human_runtime_logs(self, limit: int = 250) -> dict[str, Any]:
        raw = self.runtime_logs(limit=limit)
        return {
            "available": raw["available"],
            "lines": [_human_runtime_line(line) for line in raw["lines"]],
        }

    def log_snapshot(self, limit: int = 250, event_limit: int = 100) -> dict[str, Any]:
        """Read each source once and pair its raw and readable representations.

        This is a bounded view of existing logs, not a second transcript store.
        Source ordering is preserved; untimestamped stdout isn't assigned a
        made-up time or interleaved with structured events as if it were exact.
        """
        settings = self.container.settings.logging
        runtime = self.runtime_logs(limit=min(max(limit, 1), 1000))
        events = self.recent_logs(limit=min(max(event_limit, 1), 200))
        runtime_entries = pair_entries(
            [safe_runtime_line(line, settings) for line in runtime["lines"]]
            if runtime["available"] else [],
            "runtime", explain_runtime,
        )
        titles = (
            self._artwork_map()
            if any(event.get("event") == "ARTWORK_DETECTED" for event in events)
            else {}
        )
        event_entries = pair_entries(
            [safe_event(event, settings) for event in events], "events",
            lambda event: explain_event(event, titles),
        )
        content = {"runtime": runtime_entries, "events": event_entries}
        snapshot_id = hashlib.sha256(
            json.dumps(content, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:24]
        return {
            "snapshot_id": snapshot_id, "captured_at": now_iso(),
            "runtime_available": runtime["available"],
            "runtime_notice": (
                "" if runtime["available"] else
                "Runtime output is unavailable. It appears when the device "
                "service records activity."
            ),
            "text_visibility": {
                "user_final": settings.log_transcripts,
                "user_live": settings.log_live_stt,
                "atlas": settings.log_llm_responses,
            },
            **content,
        }
