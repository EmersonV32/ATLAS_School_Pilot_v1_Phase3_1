"""Privacy-bounded visitor onboarding with an optional device runtime bridge."""

from __future__ import annotations

import logging
from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4

from atlas.audio.devices import (
    find_alsa_playback,
    find_pulse_capture,
    find_pulse_playback,
)
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
_RUNTIME_LANGUAGES = frozenset({"en", "fr", "es", "it", "zh"})
_MAX_CAMERA_FRAME_AGE_S = 3.0


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

    def start_session(self, *, demo: bool = False) -> dict[str, Any]: ...

    def stop_session(self) -> dict[str, Any]: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _component_is_ready(value: object) -> bool:
    """Treat errors and unavailable providers as public readiness blockers."""
    if not isinstance(value, str) or not value.strip():
        return False
    lowered = value.lower()
    return "error" not in lowered and "unavailable" not in lowered


def _runtime_headset_ready(runtime: RuntimeBridge) -> bool | None:
    """Return live Shokz readiness when a device runtime exposes its settings."""
    container = getattr(runtime, "container", None)
    settings = getattr(container, "settings", None)
    hardware = getattr(settings, "hardware", None)
    headset_name = str(getattr(hardware, "headset_name", "")).strip()
    if not headset_name:
        return None
    output_name = str(getattr(hardware, "audio_output_name", "")).strip()
    output_name = output_name or headset_name
    try:
        return bool(
            find_pulse_playback(output_name)
            and find_pulse_capture(headset_name)
            and find_alsa_playback(output_name)
        )
    except Exception:
        logger.exception("Visitor headset readiness probe failed")
        return False


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
            "demo_mode": False,
            "started_at": None,
            "updated_at": now,
        }

    def bootstrap(self) -> dict:
        with self._lock:
            return {
                "mode": self.mode,
                # A running visit ends only through an explicit visitor/staff stop.
                "inactivity_timeout_seconds": 0,
                # These languages are backed by the current ATLAS speech stack in
                # both the device runtime and the local visitor preview.
                "public_languages": ["en", "fr", "es", "it", "zh-Hant"],
                # Arabic remains an interface preview until its speech path is
                # configured and tested on the Jetson.
                "preview_languages": ["ar"],
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
                self._activate_runtime_session(demo=True)
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
            self._state["demo_mode"] = True
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
            # A stale kiosk tab must never terminate an active wearable session.
            # Active visits are ended only through the explicit staff stop route.
            if self._state["phase"] == "in_use":
                return self._projection()
            self._stop_runtime_session()
            self._scenario = "ready"
            self._help_request = None
            self._state = self._new_state()
            return self._projection()

    def start_demo(
        self,
        *,
        language: str,
        profile: str,
        pack_id: str | None = None,
        accessibility_mode: bool = False,
    ) -> dict:
        """Start or restart one atomic judge demo from the admin dashboard."""
        with self._lock:
            previous_language = self._state["language"]
            self._state["language"] = language
            readiness = self._readiness()
            if readiness["blockers"]:
                self._state["language"] = previous_language
                raise RuntimeError(readiness["blockers"][0])
            if self._state["phase"] == "in_use":
                self._stop_runtime_session()
            self._state["phase"] = "starting"
            self._state["step"] = "demo"
            self._state["transfer"] = "transferring"
            self._state["demo_mode"] = True
            self._touch()
            try:
                self._activate_runtime_session(
                    demo=True,
                    profile=profile,
                    pack_id=pack_id,
                    accessibility_mode=accessibility_mode,
                )
            except Exception:
                logger.exception("Admin demo session start failed")
                self._record_transfer_failure()
                raise RuntimeError(
                    "ATLAS could not start demo mode. Check the runtime log."
                ) from None
            self._state["phase"] = "in_use"
            self._state["transfer"] = "complete"
            self._state["started_at"] = _now()
            self._touch()
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
        self._state["demo_mode"] = False
        self._touch()

    def _activate_runtime_session(
        self,
        *,
        demo: bool = False,
        profile: str | None = None,
        pack_id: str | None = None,
        accessibility_mode: bool | None = None,
    ) -> None:
        if self._runtime_service is None:
            return
        runtime_profile = profile or self._effective_runtime_profile()
        accessibility = self._state["profile"]["accessibility"]
        self._runtime_service.set_profile(
            language=self._state["language"],
            profile=runtime_profile,
            pack_id=pack_id,
            accessibility_mode=(
                "audio_description" in accessibility
                if accessibility_mode is None
                else accessibility_mode
            ),
        )
        self._runtime_service.start_session(demo=demo)

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
            self._language_item(language, supported=_RUNTIME_LANGUAGES),
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
        provider_audio_ready = _component_is_ready(
            components.get("stt")
        ) and _component_is_ready(components.get("tts"))
        headset_connected = _runtime_headset_ready(self._runtime_service)
        audio_ready = (
            headset_connected
            if headset_connected is not None
            else provider_audio_ready
        )
        connection_ready = _component_is_ready(components.get("llm"))
        content_ready = all(
            _component_is_ready(components.get(name))
            for name in ("vector_store", "fts_store", "retriever")
        )
        camera_age = camera.get("last_frame_age_s")
        camera_ready = (
            camera.get("ready") is True
            and isinstance(camera_age, (int, float))
            and 0 <= camera_age <= _MAX_CAMERA_FRAME_AGE_S
        )
        camera_error = str(camera.get("last_error") or "").strip()
        camera_disconnected = (
            not camera_ready and camera_age is None and bool(camera_error)
        )
        if camera_ready:
            camera_detail = "Camera health signal is fresh."
        elif camera_disconnected:
            camera_detail = (
                "Camera disconnected. Reconnect it when ready; this website "
                "remains available."
            )
        else:
            camera_detail = (
                "Camera stream is connected but not supplying a fresh image."
            )
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
                    "Shokz OpenComm2 input and output are ready."
                    if audio_ready
                    else (
                        "Reconnect the Shokz OpenComm2 USB adapter; this page "
                        "checks again automatically."
                        if headset_connected is False
                        else "Audio input or output is unavailable."
                    )
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
                camera_detail,
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
        normalized = str(language).strip().lower().split("-", 1)[0]
        if normalized not in supported:
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
