"""Thread-safe, mock-backed visitor onboarding state for dashboard Pass 1."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from uuid import uuid4

from atlas.dashboard.visitor_schemas import (
    VisitorHelpRequest,
    VisitorProgressRequest,
)

_INTERESTS = {
    "stories",
    "technique",
    "symbols",
    "history",
    "color-light",
    "people-society",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


class VisitorService:
    """Owns ephemeral onboarding state without touching the device runtime."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._scenario = "ready"
        self._help_request: dict | None = None
        self._state = self._new_state()

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
            return {
                "mode": "mock",
                "inactivity_timeout_seconds": 120,
                "public_languages": ["en"],
                "preview_languages": ["fr", "es", "it", "ar", "zh-Hant"],
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
                self._state["phase"] = "ready"
                self._state["transfer"] = "failed"
                self._touch()
                raise RuntimeError(
                    "The profile could not be transferred. Please retry."
                )
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
                "state": self._projection(),
                "readiness": self._readiness(),
                "help_request": deepcopy(self._help_request),
                "scenario": self._scenario,
            }

    def _touch(self) -> None:
        self._state["updated_at"] = _now()

    def _projection(self) -> dict:
        result = deepcopy(self._state)
        result["help"] = deepcopy(self._help_request)
        return result

    def _readiness(self) -> dict:
        scenario = self._scenario
        language = self._state["language"]
        items = [
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
                (
                    "Check fit and volume."
                    if scenario == "headset_attention"
                    else "Audio input and output are ready."
                ),
            ),
            self._item(
                "connection",
                "Local connection",
                "unavailable" if scenario == "connection_lost" else "ready",
                (
                    "Connection to the ATLAS unit is unavailable."
                    if scenario == "connection_lost"
                    else "Private local link is ready."
                ),
            ),
            self._item("camera", "Camera", "ready", "Camera health signal is fresh."),
            self._item(
                "content",
                "Museum content",
                "ready",
                "The local content pack is available.",
            ),
            self._item(
                "language",
                "Language support",
                "pending" if language is None else "ready",
                (
                    "Choose a language to continue."
                    if language is None
                    else "Speech and responses are available."
                ),
            ),
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

    @staticmethod
    def _item(item_id: str, label: str, status: str, detail: str) -> dict:
        return {"id": item_id, "label": label, "status": status, "detail": detail}
