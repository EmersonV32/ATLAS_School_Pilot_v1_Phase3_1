"""RuntimeService: the dashboard's bridge into the ATLAS container.

Holds the teacher-facing session state (language, profile, pack, manual
artwork override) and exposes privacy-safe operations for the API layer.
All heavy components come from the existing dependency container — this
module never constructs its own pipeline.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from atlas.app.dependency_container import Container
from atlas.models.enums import EducationalLevel, Language, RunMode
from atlas.models.retrieval import RetrievalQuery
from atlas.utils.ids import new_session_id
from atlas.utils.time import Timer

logger = logging.getLogger(__name__)

_DEFAULT_PROFILE = EducationalLevel.ADULT_BEGINNER.value


def _to_language(value: str | None, fallback: str = "en") -> Language:
    try:
        return Language(str(value).lower())
    except (ValueError, TypeError):
        return Language(fallback)


def _to_level(value: str | None) -> EducationalLevel:
    try:
        return EducationalLevel(str(value).lower())
    except (ValueError, TypeError):
        return EducationalLevel.ADULT_BEGINNER


class RuntimeService:
    def __init__(self, container: Container) -> None:
        self.container = container
        self.session_id: str | None = None
        self.language: str = "en"
        self.profile: str = _DEFAULT_PROFILE
        self.pack_id: str = container.settings.default_pack_id
        self.accessibility_mode: bool = False
        self.last_answer: dict[str, Any] | None = None
        # Demo-only simulation flags (never active outside dev/demo mode).
        self.demo_flags: set[str] = set()

    # -- session -----------------------------------------------------------
    def start_session(self) -> dict[str, Any]:
        self.session_id = new_session_id()
        self.container.logger.log(
            session_id=self.session_id, state="session", event="session_start"
        )
        return {"session_id": self.session_id}

    def stop_session(self) -> dict[str, Any]:
        if self.session_id:
            self.container.logger.log(
                session_id=self.session_id, state="session", event="session_stop"
            )
        stopped = self.session_id
        self.session_id = None
        return {"stopped_session_id": stopped}

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

    def artwork_status(self) -> dict[str, Any]:
        status = self.container.artwork_tracker.status()
        if "low_confidence" in self.demo_flags:
            status["confidence"] = 0.30
            status["stable"] = False
            status["warning"] = "low_confidence (simulated)"
        return status

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
        artwork = self.artwork_status()
        artwork_id = artwork.get("artwork_id")

        if "llm_timeout" in self.demo_flags:
            fallback = (
                "Je suis désolé, je ne peux pas répondre en ce moment."
                if lang == Language.FR
                else "I'm sorry, I can't generate a response right now."
            )
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

        session_id = self.session_id or "no_session"
        log_fields: dict[str, Any] = {
            "language": lang.value,
            "artwork_id": artwork_id,
            "retrieval_latency_ms": result.total_latency_ms,
            "fallback_used": dialogue.fallback_used,
        }
        settings = self.container.settings
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
        if mode not in (RunMode.DEV, RunMode.DEMO):
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
            components["stt"] = type(c.stt).__name__
            components["tts"] = type(c.tts).__name__
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
            "experience": self.experience_settings(),
            "artwork": self.artwork_status(),
            "last_answer": last,
            "demo_flags": sorted(self.demo_flags),
            "privacy": {
                "store_raw_audio": settings.privacy.store_raw_audio,
                "store_raw_images": settings.privacy.store_raw_images,
                "store_face_data": settings.privacy.store_face_data,
                "anonymous_session_ids": settings.privacy.anonymous_session_ids,
                "transcript_logging": settings.logging.log_transcripts,
                "cloud_llm_enabled": settings.llm.cloud_llm_enabled,
                "cloud_llm_provider": settings.llm.provider,
            },
            "emergency_stopped": bool(
                getattr(self.container.hardware, "emergency_stopped", False)
            ),
        }

    def recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.container.logger.read_recent(limit=limit)
