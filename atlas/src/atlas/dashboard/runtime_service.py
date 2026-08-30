"""RuntimeService: the dashboard's bridge into the ATLAS container.

Holds the teacher-facing session state (language, profile, pack, manual
artwork override) and exposes privacy-safe operations for the API layer.
All heavy components come from the existing dependency container — this
module never constructs its own pipeline.
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from atlas.app.dependency_container import Container
from atlas.config.settings import Settings
from atlas.models.enums import EducationalLevel, Language, RunMode
from atlas.models.retrieval import RetrievalQuery
from atlas.utils.ids import new_session_id
from atlas.utils.time import Timer

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
        names = {
            "en": "English",
            "fr": "French",
            "es": "Spanish",
            "it": "Italian",
            "ar": "Arabic",
            "zh": "Mandarin",
        }
        language_code = (language.group(1) if language else "").split("-")[0]
        language_name = names.get(language_code, "the selected language")
        timeout_text = timeout.group(1) if timeout else "the configured window"
        return (
            f"ATLAS is listening in {language_name} for up to {timeout_text}."
        )
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
    try:
        return Language(str(value).strip().lower().split("-", 1)[0])
    except (ValueError, TypeError):
        return Language(fallback)


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
    ) -> None:
        self.container = container
        self._capture_request = capture_request
        self.session_id: str | None = None
        self.language: str = "en"
        self.profile: str = _DEFAULT_PROFILE
        self.pack_id: str = container.settings.default_pack_id
        self.accessibility_mode: bool = False
        self.demo_active: bool = False
        self.last_answer: dict[str, Any] | None = None
        self._pending_settings: Settings | None = None
        # Demo-only simulation flags (never active outside dev/demo mode).
        self.demo_flags: set[str] = set()

    # -- session -----------------------------------------------------------
    def start_session(self, *, demo: bool = False) -> dict[str, Any]:
        self.container.dialogue_engine.reset_conversation()
        self.demo_active = bool(demo)
        self.session_id = new_session_id()
        self.container.logger.log(
            session_id=self.session_id,
            state="session",
            event="demo_start" if self.demo_active else "session_start",
        )
        return {"session_id": self.session_id, "demo_active": self.demo_active}

    def stop_session(self) -> dict[str, Any]:
        if self.session_id:
            self.container.logger.log(
                session_id=self.session_id, state="session", event="session_stop"
            )
        stopped = self.session_id
        self.session_id = None
        self.demo_active = False
        self.container.dialogue_engine.reset_conversation()
        return {"stopped_session_id": stopped, "demo_active": False}

    def set_profile(
        self,
        language: str | None = None,
        profile: str | None = None,
        pack_id: str | None = None,
        accessibility_mode: bool | None = None,
    ) -> dict[str, Any]:
        if language is not None:
            self.language = _to_language(language).value
        if profile is not None:
            self.profile = _to_level(profile).value
        if pack_id is not None:
            self.pack_id = pack_id
        if accessibility_mode is not None:
            self.accessibility_mode = bool(accessibility_mode)
            if self.accessibility_mode:
                self.profile = EducationalLevel.VISUAL_IMPAIRMENT.value
        return self.experience_settings()

    def experience_settings(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "profile": self.profile,
            "pack_id": self.pack_id,
            "accessibility_mode": self.accessibility_mode,
        }

    # -- artwork context -----------------------------------------------------
    def set_manual_artwork(self, artwork_id: str) -> dict[str, Any]:
        known = self._artwork_map()
        if known and artwork_id not in known:
            raise ValueError(f"unknown artwork_id: {artwork_id}")
        self.container.artwork_tracker.set_manual_override(
            artwork_id, label=known.get(artwork_id)
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
        self.container.artwork_tracker.set_manual_override(
            detection.artwork_id, detection.label
        )
        status = self.container.artwork_tracker.status()
        status["capture_source"] = "manual_center_crop"
        return status

    def artwork_status(self) -> dict[str, Any]:
        status = self.container.artwork_tracker.status()
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

        ok, encoded = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        )
        if not ok:
            raise RuntimeError("camera frame encoding failed")
        return encoded.tobytes()

    def _artwork_map(self) -> dict[str, str]:
        """artwork_id -> title for the selected pack."""
        from atlas.rag.ingest import load_content_pack

        pack_dir = (
            Path(self.container.settings.paths.content_packs_dir) / self.pack_id
        )
        if not (pack_dir / "manifest.json").exists():
            return {}
        try:
            pack = load_content_pack(pack_dir)
        except Exception:
            return {}
        return {a.artwork_id: a.title for a in pack.artworks}

    # -- typed-question fallback ----------------------------------------------
    def ask(
        self,
        question: str,
        language: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        lang = _to_language(language or self.language)
        level = _to_level(profile or self.profile)
        settings = self.container.settings
        if settings.logging.log_transcripts:
            logger.info("[Typed question] %s", question)
        artwork = self.artwork_status()
        artwork_id = artwork.get("artwork_id")

        if "llm_timeout" in self.demo_flags:
            timeout_fallbacks = {
                Language.EN: "I'm sorry, I can't generate a response right now.",
                Language.FR: "Je suis désolé, je ne peux pas répondre en ce moment.",
                Language.ES: (
                    "Lo siento, no puedo generar una respuesta en este momento."
                ),
                Language.IT: (
                    "Mi dispiace, non posso generare una respuesta in questo "
                    "momento."
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
            result = self.container.retriever.retrieve(
                RetrievalQuery(
                    text=question,
                    artwork_id=artwork_id,
                    language=lang,
                    educational_level=level,
                )
            )
            chunks = [
                {"text": c.text, "chunk_id": c.chunk_id} for c in result.chunks
            ]
            dialogue = self.container.dialogue_engine.respond(
                question=question,
                artwork_chunks=chunks,
                language=lang.value,
                profile=level.value,
                artwork_id=artwork_id,
            )

        answer = {
            "answer": dialogue.response,
            "language": dialogue.language,
            "grounded": dialogue.grounded,
            "fallback_used": dialogue.fallback_used,
            "filtered": dialogue.filtered,
            "confidence": dialogue.confidence,
            "used_chunk_ids": dialogue.used_chunk_ids,
            "artwork_id": artwork_id,
            "retrieval_latency_ms": result.total_latency_ms,
            "total_latency_ms": total.elapsed_ms,
            "error": dialogue.error,
        }
        self.last_answer = answer
        if settings.logging.log_llm_responses:
            logger.info("[LLM final] %s", dialogue.response)
        logger.info(
            "[Timing] Typed question total %.0f ms "
            "[retrieval_ms=%s grounded=%s fallback=%s error=%s]",
            total.elapsed_ms,
            (
                f"{result.total_latency_ms:.0f}"
                if result.total_latency_ms is not None
                else "n/a"
            ),
            dialogue.grounded,
            dialogue.fallback_used,
            dialogue.error or "none",
        )

        session_id = self.session_id or "no_session"
        log_fields: dict[str, Any] = {
            "language": lang.value,
            "artwork_id": artwork_id,
            "retrieval_latency_ms": result.total_latency_ms,
            "fallback_used": dialogue.fallback_used,
        }
        if settings.logging.log_transcripts:
            transcript = question
            if settings.privacy.transcript_logging_sanitized:
                transcript = transcript[:200]
            log_fields["transcript"] = transcript
        self.container.logger.log(
            session_id=session_id,
            state="dashboard",
            event="typed_question",
            **log_fields,
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

        pack_dir = (
            Path(self.container.settings.paths.content_packs_dir) / pack_id
        )
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
                "silero_threshold": speech.silero_threshold,
                "silero_min_silence_ms": speech.silero_min_silence_ms,
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
    def emergency_stop(self) -> dict[str, Any]:
        self.container.hardware.emergency_stop()
        return {"emergency_stopped": True}

    def clear_emergency_stop(self) -> dict[str, Any]:
        self.container.hardware.clear_emergency_stop()
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
            components["vector_store"] = (
                "ok" if c.vector_store.count() > 0 else "empty"
            )
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
            "emergency_stopped": bool(
                getattr(c.hardware, "emergency_stopped", False)
            ),
        }

    def status(self) -> dict[str, Any]:
        settings = self.container.settings
        try:
            camera_status = self.container.camera_source.status()
        except Exception as exc:
            camera_status = {
                "ready": False,
                "last_frame_age_s": None,
                "last_error": f"{type(exc).__name__}: {exc}",
            }
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
            "experience": self.experience_settings(),
            "artwork": self.artwork_status(),
            "camera": camera_status,
            "last_answer": last,
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
