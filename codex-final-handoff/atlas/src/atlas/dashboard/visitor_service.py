"""Privacy-bounded visitor onboarding with an optional device runtime bridge."""

from __future__ import annotations

import logging
from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4

from atlas.dashboard.visitor_schemas import (
    VisitorHelpRequest,
    VisitorProgressRequest,
)

logger = logging.getLogger(__name__)

_INTERESTS = {
    "stories",
    "technique",
    "symbols",
    "history",
    "color-light",
    "people-society",
}
_RUNTIME_LANGUAGES = frozenset({"en", "fr", "es", "it"})


class RuntimeBridge(Protocol):
    """The minimal, non-sensitive surface shared with the device runtime."""

    def health(self) -> dict[str, Any]: ...

    def status(self) -> dict[str, Any]: ...

    def set_profile(
        self,
        language: str | None = None,
        profile: str | None = None,
        pack_id: str | None = None,
        accessibility_mode: bool | None = None,
    ) -> dict[str, Any]: ...

    def start_session(self) -> dict[str, Any]: ...

    def stop_session(self) -> dict[str, Any]: ...


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _component_is_ready(value: object) -> bool:
    """Treat errors and unavailable providers as public readiness blockers."""
    if not isinstance(value, str) or not value.strip():
        return False
    lowered = value.lower()
    return "error" not in lowered and "unavailable" not in lowered


class VisitorService:
    """Owns ephemeral onboarding and optionally activates one device session.

    Names, exact ages, raw media, prompts, transcript text, and answer text do
    not cross this boundary. In development, ``runtime_service`` stays ``None``
    so the full visitor dashboard remains mock-backed and easy to test.
    """

    def __init__(self, runtime_service: RuntimeBridge | None = None) -> None:
        self._lock = RLock()
        self._runtime_service = runtime_service
        self._scenario = "ready"
        self._help_request: dict | None = None
        self._state = self._new_state()

    @property
    def mode(self) -> str:
        return "runtime" if self._runtime_service is not None else "mock"

    @staticmethod
    def _new_state() -> dict:
        now = _now()
        return {
            "unit_id": "ATLAS-01",
            "phase": "idle",
            "step": "welcome",
            "language": None,
            "profile": {
                "name_entered": False,
                "age_guidance": None,
                "expertise": None,
                "interests": [],
                "accessibility": [],
            },
            "connection": "online",
            "transfer": "idle",
            "started_at": None,
            "updated_at": now,
        }

    def bootstrap(self) -> dict:
        with self._lock:
            runtime_active = self._runtime_service is not None
            return {
                "mode": self.mode,
                "inactivity_timeout_seconds": 120,
                "public_languages": (
                    ["en", "fr", "es", "it"] if runtime_active else ["en"]
                ),
                "preview_languages": (
                    ["ar", "zh-Hant"]
                    if runtime_active
                    else ["fr", "es", "it", "ar", "zh-Hant"]
                ),
                "interest_manifest_url": "/static/visitor/interests.json",
                "state": self._projection(),
                "readiness": self._readiness(),
            }

    def progress(self, request: VisitorProgressRequest) -> dict:
        unknown = set(request.interests) - _INTERESTS
        if unknown:
            raise ValueError(f"unknown interest selection: {sorted(unknown)[0]}")
        with self._lock:
            self._state["phase"] = "onboarding"
            self._state["step"] = request.step
            self._state["language"] = request.language
            self._state["profile"] = {
                "name_entered": request.name_entered,
                "age_guidance": request.age_guidance,
                "expertise": request.expertise,
                "interests": list(request.interests),
                "accessibility": list(request.accessibility),
            }
            self._touch()
            return self._projection()

    def readiness(self) -> dict:
        with self._lock:
            return self._readiness()

    def start(self) -> dict:
        with self._lock:
            readiness = self._readiness()
            if readiness["blockers"]:
                raise RuntimeError(readiness["blockers"][0])
            self._state["phase"] = "starting"
            self._state["transfer"] = "transferring"
            self._touch()
            if self._scenario == "transfer_failure":
                self._record_transfer_failure()
                raise RuntimeError(
                    "The profile could not be transferred. Please retry."
                )
            try:
                self._activate_runtime_session()
            except Exception:
                logger.exception("Visitor runtime session start failed")
                self._record_transfer_failure()
                raise RuntimeError(
                    "ATLAS could not start the experience. Please ask a staff "
                    "member to check the unit."
                ) from None
            self._state["phase"] = "in_use"
            self._state["step"] = "privacy"
            self._state["transfer"] = "complete"
            self._state["started_at"] = _now()
            self._touch()
            return self._projection()

    def request_help(self, request: VisitorHelpRequest) -> dict:
        with self._lock:
            if self._help_request and self._help_request["status"] == "requested":
                return deepcopy(self._help_request)
            self._help_request = {
                "request_id": uuid4().hex,
                "status": "requested",
                "context": request.context,
                "message": request.message,
                "requested_at": _now(),
                "acknowledged_at": None,
            }
            self._touch()
            return deepcopy(self._help_request)

    def acknowledge_help(self, request_id: str) -> dict:
        with self._lock:
            if not self._help_request or self._help_request["request_id"] != request_id:
                raise KeyError("help request not found")
            if self._help_request["status"] != "acknowledged":
                self._help_request["status"] = "acknowledged"
                self._help_request["acknowledged_at"] = _now()
                self._touch()
            return deepcopy(self._help_request)

    def stop(self) -> dict:
        with self._lock:
            already_stopped = self._state["phase"] in {"idle", "thank_you"}
            self._stop_runtime_session()
            unit_id = self._state["unit_id"]
            connection = self._state["connection"]
            self._state = self._new_state()
            self._state.update(
                {
                    "unit_id": unit_id,
                    "phase": "thank_you",
                    "step": "welcome",
                    "connection": connection,
                    "transfer": "idle",
                }
            )
            self._help_request = None
            return {"stopped": not already_stopped, "state": self._projection()}

    def reset(self) -> dict:
        with self._lock:
            self._stop_runtime_session()
            self._scenario = "ready"
            self._help_request = None
            self._state = self._new_state()
            return self._projection()

    def simulate(self, scenario: str) -> dict:
        with self._lock:
            if scenario == "reset":
                self._scenario = "ready"
                self._state["connection"] = "online"
                if self._state["transfer"] == "failed":
                    self._state["transfer"] = "idle"
            else:
                self._scenario = scenario
                self._state["connection"] = (
                    "offline" if scenario == "connection_lost" else "online"
                )
            self._touch()
            return {
                "scenario": self._scenario,
                "state": self._projection(),
                "readiness": self._readiness(),
            }

    def live_status(self) -> dict:
        with self._lock:
            return {
                "mode": self.mode,
                "state": self._projection(),
                "readiness": self._readiness(),
                "help_request": deepcopy(self._help_request),
                "scenario": self._scenario,
            }

    def _record_transfer_failure(self) -> None:
        self._state["phase"] = "ready"
        self._state["transfer"] = "failed"
        self._touch()

    def _activate_runtime_session(self) -> None:
        if self._runtime_service is None:
            return
        profile = self._effective_runtime_profile()
        accessibility = self._state["profile"]["accessibility"]
        self._runtime_service.set_profile(
            language=self._state["language"],
            profile=profile,
            accessibility_mode="audio_description" in accessibility,
        )
        self._runtime_service.start_session()

    def _stop_runtime_session(self) -> None:
        if self._runtime_service is None:
            return
        try:
            self._runtime_service.stop_session()
        except Exception:
            # The kiosk must still clear its local, non-sensitive state after a
            # staff stop or timeout. The admin runtime log keeps the traceback.
            logger.exception("Visitor runtime session stop failed")

    def _effective_runtime_profile(self) -> str:
        profile = self._state["profile"]
        accessibility = set(profile["accessibility"])
        if "audio_description" in accessibility:
            return "visual_impairment"
        if "simple_language" in accessibility:
            return "simple_language"
        if profile["age_guidance"] == "under_13":
            return "child"
        if profile["age_guidance"] == "13_17":
            return "teen"
        if profile["expertise"] == "enthusiast":
            return "expert"
        return "adult_beginner"

    def _touch(self) -> None:
        self._state["updated_at"] = _now()

    def _projection(self) -> dict:
        result = deepcopy(self._state)
        result["help"] = deepcopy(self._help_request)
        return result

    def _readiness(self) -> dict:
        scenario = self._scenario
        language = self._state["language"]
        if self._runtime_service is None:
            items = self._mock_readiness_items(scenario, language)
        else:
            items = self._runtime_readiness_items(scenario, language)
        blocking_states = {"unavailable", "unsupported", "pending"}
        blockers = [
            item["detail"] for item in items if item["status"] in blocking_states
        ]
        return {
            "ready": not blockers,
            "items": items,
            "blockers": blockers,
            "checked_at": _now(),
        }

    def _mock_readiness_items(self, scenario: str, language: str | None) -> list[dict]:
        return [
            self._item(
                "unit",
                "Wearable unit",
                "unavailable" if scenario == "unit_unavailable" else "ready",
                "Unit is assigned and responding.",
            ),
            self._item(
                "headset",
                "Headset",
                "degraded" if scenario == "headset_attention" else "ready",
                "Check fit and volume."
                if scenario == "headset_attention"
                else "Audio input and output are ready.",
            ),
            self._item(
                "connection",
                "Local connection",
                "unavailable" if scenario == "connection_lost" else "ready",
                "Connection to the ATLAS unit is unavailable."
                if scenario == "connection_lost"
                else "Private local link is ready.",
            ),
            self._item(
                "camera", "Camera", "ready", "Camera health signal is fresh."
            ),
            self._item(
                "content",
                "Museum content",
                "ready",
                "The local content pack is available.",
            ),
            self._language_item(language, supported={"en"}),
            self._item(
                "safety", "Safety controls", "ready", "Emergency stop is clear."
            ),
            self._item(
                "profile",
                "Visitor profile",
                "ready",
                "Only coarse preferences will transfer.",
            ),
        ]

    def _runtime_readiness_items(
        self, scenario: str, language: str | None
    ) -> list[dict]:
        if scenario == "unit_unavailable":
            return self._runtime_unavailable_items(language, "ATLAS is not responding.")
        if scenario == "connection_lost":
            return self._runtime_unavailable_items(
                language, "Connection to the ATLAS unit is unavailable."
            )
        try:
            health = self._runtime_service.health()
            status = self._runtime_service.status()
        except Exception:
            logger.exception("Visitor readiness check could not read the runtime")
            return self._runtime_unavailable_items(
                language, "ATLAS is not responding. Please ask a staff member."
            )

        components = health.get("components", {})
        if not isinstance(components, dict):
            components = {}
        camera = status.get("camera", {})
        if not isinstance(camera, dict):
            camera = {}
        unit_ready = health.get("status") == "ok"
        audio_ready = _component_is_ready(
            components.get("stt")
        ) and _component_is_ready(components.get("tts"))
        connection_ready = _component_is_ready(components.get("llm"))
        content_ready = all(
            _component_is_ready(components.get(name))
            for name in ("vector_store", "fts_store", "retriever")
        )
        camera_ready = camera.get("ready") is True
        emergency_stopped = bool(status.get("emergency_stopped"))
        self._state["connection"] = "online" if connection_ready else "offline"

        return [
            self._item(
                "unit",
                "Wearable unit",
                "ready" if unit_ready else "unavailable",
                "ATLAS is ready." if unit_ready else "ATLAS is not responding.",
            ),
            self._item(
                "headset",
                "Headset",
                "degraded" if scenario == "headset_attention" else (
                    "ready" if audio_ready else "unavailable"
                ),
                "Check fit and volume."
                if scenario == "headset_attention"
                else (
                    "Audio input and output are ready."
                    if audio_ready
                    else "Audio input or output is unavailable."
                ),
            ),
            self._item(
                "connection",
                "Local connection",
                "ready" if connection_ready else "unavailable",
                "Private local link is ready."
                if connection_ready
                else "Connection to the ATLAS unit is unavailable.",
            ),
            self._item(
                "camera",
                "Camera",
                "ready" if camera_ready else "unavailable",
                "Camera health signal is fresh."
                if camera_ready
                else "Camera is not supplying a fresh image.",
            ),
            self._item(
                "content",
                "Museum content",
                "ready" if content_ready else "unavailable",
                "The local content pack is available."
                if content_ready
                else "Museum content is unavailable.",
            ),
            self._language_item(language, supported=_RUNTIME_LANGUAGES),
            self._item(
                "safety",
                "Safety controls",
                "unavailable" if emergency_stopped else "ready",
                "Emergency stop must be cleared before starting."
                if emergency_stopped
                else "Emergency stop is clear.",
            ),
            self._item(
                "profile",
                "Visitor profile",
                "ready",
                "Only coarse preferences will transfer.",
            ),
        ]

    def _runtime_unavailable_items(
        self, language: str | None, detail: str
    ) -> list[dict]:
        self._state["connection"] = "offline"
        return [
            self._item("unit", "Wearable unit", "unavailable", detail),
            self._item("headset", "Headset", "pending", "Waiting for ATLAS."),
            self._item("connection", "Local connection", "unavailable", detail),
            self._item("camera", "Camera", "pending", "Waiting for ATLAS."),
            self._item("content", "Museum content", "pending", "Waiting for ATLAS."),
            self._language_item(language, supported=_RUNTIME_LANGUAGES),
            self._item("safety", "Safety controls", "pending", "Waiting for ATLAS."),
            self._item(
                "profile",
                "Visitor profile",
                "ready",
                "Only coarse preferences will transfer.",
            ),
        ]

    def _language_item(
        self, language: str | None, supported: set[str] | frozenset[str]
    ) -> dict:
        if language is None:
            return self._item(
                "language",
                "Language support",
                "pending",
                "Choose a language to continue.",
            )
        if language not in supported:
            return self._item(
                "language",
                "Language support",
                "unsupported",
                "Choose a language available on this ATLAS unit.",
            )
        return self._item(
            "language",
            "Language support",
            "ready",
            "Speech and responses are available.",
        )

    @staticmethod
    def _item(item_id: str, label: str, status: str, detail: str) -> dict:
        return {"id": item_id, "label": label, "status": status, "detail": detail}
