"""Contract, lifecycle, privacy, and shell tests for visitor onboarding."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from atlas.app.dependency_container import Container
from atlas.config.settings import DashboardSettings, PathsSettings, Settings
from atlas.dashboard.api import create_app
from atlas.dashboard.visitor_schemas import VisitorProgressRequest
from atlas.dashboard.visitor_service import VisitorService

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "src" / "atlas" / "dashboard" / "static"
ADMIN_TOKEN = "visitor-test-admin-token"


@pytest.fixture()
def visitor_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("ATLAS_ADMIN_TOKEN", ADMIN_TOKEN)
    for subdirectory in ("content", "chroma", "sqlite", "logs"):
        (tmp_path / subdirectory).mkdir()
    settings = Settings(
        paths=PathsSettings(
            data_dir=tmp_path,
            content_packs_dir=tmp_path / "content",
            chroma_dir=tmp_path / "chroma",
            sqlite_dir=tmp_path / "sqlite",
            logs_dir=tmp_path / "logs",
        ),
        dashboard=DashboardSettings(
            config_override_path=tmp_path / "dashboard_overrides.yaml"
        ),
    )
    return TestClient(create_app(Container(settings)))


def _admin() -> dict[str, str]:
    return {"X-Atlas-Admin-Token": ADMIN_TOKEN}


def _progress(**updates) -> dict:
    payload = {
        "step": "language",
        "language": "en",
        "name_entered": False,
        "age_guidance": None,
        "expertise": None,
        "interests": [],
        "accessibility": [],
    }
    payload.update(updates)
    return payload


class _FakeRuntime:
    def __init__(self, *, camera_ready: bool = True) -> None:
        self.camera_ready = camera_ready
        self.profile_calls: list[dict] = []
        self.started = 0
        self.stopped = 0

    def health(self) -> dict:
        return {
            "status": "ok",
            "components": {
                "stt": "DeepgramSTT",
                "tts": "CartesiaTTS",
                "llm": "GeminiClient",
                "vector_store": "ok",
                "fts_store": "ok (fts5)",
                "retriever": "HybridRetriever",
            },
        }

    def status(self) -> dict:
        return {
            "camera": {"ready": self.camera_ready},
            "emergency_stopped": False,
        }

    def set_profile(self, **kwargs) -> dict:
        self.profile_calls.append(kwargs)
        return kwargs

    def start_session(self) -> dict:
        self.started += 1
        return {"session_id": "anonymous-session"}

    def stop_session(self) -> dict:
        self.stopped += 1
        return {"stopped_session_id": "anonymous-session"}


class TestVisitorShell:
    def test_root_is_onboarding_only(self, visitor_client):
        response = visitor_client.get("/")
        assert response.status_code == 200
        assert "Meet art through" in response.text
        assert "Start my experience" in response.text
        assert "OpenComm2" in response.text
        assert 'id="age-keypad"' in response.text
        assert "Available today" not in response.text
        assert "Onboarding live monitor" not in response.text
        for prohibited in ("Live camera", "YOLO", "Provider", "Latency"):
            assert prohibited not in response.text

    def test_admin_keeps_operations_and_adds_live_monitor(self, visitor_client):
        response = visitor_client.get("/admin")
        assert response.status_code == 200
        assert "Onboarding live monitor" in response.text
        assert "Live camera" in response.text
        assert "Live logs" in response.text
        assert "Stop &amp; clear" in response.text

    def test_shell_has_accessibility_and_pwa_hooks(self, visitor_client):
        html = visitor_client.get("/").text
        assert '<main id="visitor-app"' in html
        assert 'aria-live="polite"' in html
        assert 'aria-label="Setup progress"' in html
        assert 'rel="manifest"' in html
        css = (STATIC_DIR / "visitor.css").read_text(encoding="utf-8")
        assert "prefers-reduced-motion" in css
        assert ":focus-visible" in css

    def test_service_worker_caches_only_explicit_static_shell(self, visitor_client):
        response = visitor_client.get("/service-worker.js")
        assert response.status_code == 200
        assert response.headers["service-worker-allowed"] == "/"
        assert "STATIC_ALLOWLIST" in response.text
        assert 'CACHE_NAME = "atlas-visitor-shell-v11"' in response.text
        assert '"/static/visitor.js?v=11"' in response.text
        assert '"/static/visitor/assets/expertise-triptych.png"' in response.text
        assert '"/static/visitor/locales/fr.json"' in response.text
        assert '"/api/' not in response.text
        assert 'request.method !== "GET"' in response.text

    def test_visitor_shell_uses_the_current_service_worker_asset_version(
        self, visitor_client
    ):
        html = visitor_client.get("/").text
        assert "/static/visitor.css?v=11" in html
        assert "/static/visitor.js?v=11" in html

    def test_language_selection_localizes_without_mirroring_navigation(
        self, visitor_client
    ):
        html = visitor_client.get("/").text
        source = (STATIC_DIR / "visitor.js").read_text(encoding="utf-8")
        html_keys = set(re.findall(r'data-i18n="([^"]+)"', html))

        assert "document.documentElement.dir = \"ltr\"" in source
        assert 'classList.toggle("is-rtl-language"' in source
        assert "Interface copy remains in English" not in source
        for locale_name in ("fr", "es", "it", "ar", "zh-Hant"):
            locale = json.loads(
                (STATIC_DIR / "visitor" / "locales" / f"{locale_name}.json")
                .read_text(encoding="utf-8")
            )
            assert html_keys <= set(locale["strings"])

    def test_age_is_entered_with_private_numeric_keypad(self, visitor_client):
        html = visitor_client.get("/").text
        source = (STATIC_DIR / "visitor.js").read_text(encoding="utf-8")

        assert 'id="visitor-age" type="text" readonly inputmode="none"' in html
        assert html.count('data-digit="') == 10
        assert "ageGuidance = age < 13" in source
        assert '"age":' not in source

    def test_help_request_has_a_prominent_admin_state(self, visitor_client):
        html = visitor_client.get("/admin").text
        source = (STATIC_DIR / "admin.js").read_text(encoding="utf-8")
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

        assert 'id="visitor-assistance"' in html
        assert 'aria-live="assertive"' in html
        assert "HELP REQUEST · ATLAS Admin" in source
        assert ".visitor-live-panel.has-help-request" in css

    def test_interest_assets_are_local_and_marked_unapproved(self):
        manifest = json.loads(
            (STATIC_DIR / "visitor" / "interests.json").read_text(encoding="utf-8")
        )
        assert manifest["development_placeholders"] is True
        assert len(manifest["interests"]) == 6
        assert all(item["approved"] is False for item in manifest["interests"])
        for item in manifest["interests"]:
            path = STATIC_DIR / item["asset"].removeprefix("/static/")
            assert path.is_file()

    def test_journey_publishes_the_destination_screen_before_rendering_it(self):
        source = (STATIC_DIR / "visitor.js").read_text(encoding="utf-8")
        go_next = source.split("async function goNext() {", 1)[1].split(
            "\n}\n\nasync function goBack()",
            1,
        )[0]
        go_back = source.split("async function goBack() {", 1)[1].split(
            "\n}\n\nfunction readinessIcon",
            1,
        )[0]

        assert "await saveProgress(next);" in go_next
        assert "saveProgress(current)" not in go_next
        assert go_next.index("await saveProgress(next);") < go_next.index(
            "showScreen(next);"
        )
        assert "await saveProgress(previous);" in go_back
        assert go_back.index("await saveProgress(previous);") < go_back.index(
            "showScreen(previous);"
        )


class TestVisitorContract:
    def test_bootstrap_is_mock_backed_and_private(self, visitor_client):
        body = visitor_client.get("/api/visitor/bootstrap").json()
        assert body["mode"] == "mock"
        assert body["inactivity_timeout_seconds"] == 120
        assert body["public_languages"] == ["en"]
        assert body["state"]["phase"] == "idle"
        assert body["state"]["profile"]["name_entered"] is False

    @pytest.mark.parametrize(
        "forbidden_field", ["name", "first_name", "age", "exact_age"]
    )
    def test_identity_fields_are_rejected(self, visitor_client, forbidden_field):
        payload = _progress()
        payload[forbidden_field] = "Ada" if "name" in forbidden_field else 16
        response = visitor_client.post(
            "/api/visitor/onboarding/progress", json=payload
        )
        assert response.status_code == 422

    def test_language_is_the_only_required_personalization(self, visitor_client):
        blocked = visitor_client.post("/api/visitor/onboarding/start")
        assert blocked.status_code == 409
        assert "language" in blocked.json()["detail"].lower()

        response = visitor_client.post(
            "/api/visitor/onboarding/progress",
            json=_progress(step="privacy"),
        )
        assert response.status_code == 200
        started = visitor_client.post("/api/visitor/onboarding/start")
        assert started.status_code == 200
        assert started.json()["phase"] == "in_use"

    def test_optional_fields_do_not_block_start(self, visitor_client):
        visitor_client.post(
            "/api/visitor/onboarding/progress",
            json=_progress(step="privacy", name_entered=False),
        )
        readiness = visitor_client.get("/api/visitor/readiness").json()
        assert readiness["ready"] is True
        assert readiness["blockers"] == []

    def test_unknown_interest_is_rejected(self, visitor_client):
        response = visitor_client.post(
            "/api/visitor/onboarding/progress",
            json=_progress(interests=["not-in-the-approved-manifest"]),
        )
        assert response.status_code == 400

    def test_projection_contains_no_name_or_exact_age_value(self, visitor_client):
        visitor_client.post(
            "/api/visitor/onboarding/progress",
            json=_progress(
                step="interests",
                name_entered=True,
                age_guidance="13_17",
                interests=["stories"],
            ),
        )
        responses = [
            visitor_client.get("/api/visitor/bootstrap").json(),
            visitor_client.get("/api/admin/live-status", headers=_admin()).json(),
            visitor_client.get("/status").json(),
            visitor_client.get("/logs/recent").json(),
        ]
        serialized = json.dumps(responses)
        assert "Ada" not in serialized
        assert '"age":' not in serialized
        assert '"name":' not in serialized
        assert '"exact_age":' not in serialized
        assert '"name_entered": true' in serialized
        assert '"age_guidance": "13_17"' in serialized


class TestVisitorLifecycle:
    def test_admin_live_routes_require_authentication(self, visitor_client):
        assert visitor_client.get("/api/admin/live-status").status_code == 401
        assert visitor_client.post("/api/admin/session/stop").status_code == 401
        assert visitor_client.post(
            "/api/admin/visitor/simulate", json={"scenario": "ready"}
        ).status_code == 401

    def test_help_request_is_idempotent_and_acknowledgeable(self, visitor_client):
        first = visitor_client.post(
            "/api/visitor/help", json={"context": "headset"}
        ).json()
        second = visitor_client.post(
            "/api/visitor/help", json={"context": "headset"}
        ).json()
        assert second["request_id"] == first["request_id"]
        assert first["status"] == "requested"

        acknowledged = visitor_client.post(
            f"/api/admin/help/{first['request_id']}/acknowledge",
            headers=_admin(),
        )
        assert acknowledged.status_code == 200
        assert acknowledged.json()["status"] == "acknowledged"

    def test_admin_stop_is_idempotent_and_clears_profile(self, visitor_client):
        visitor_client.post(
            "/api/visitor/onboarding/progress",
            json=_progress(
                name_entered=True,
                age_guidance="18_plus",
                expertise="enthusiast",
                interests=["technique", "history"],
            ),
        )
        first = visitor_client.post("/api/admin/session/stop", headers=_admin())
        second = visitor_client.post("/api/admin/session/stop", headers=_admin())
        assert first.json()["stopped"] is True
        assert second.json()["stopped"] is False
        state = second.json()["state"]
        assert state["phase"] == "thank_you"
        assert state["language"] is None
        assert state["profile"] == {
            "name_entered": False,
            "age_guidance": None,
            "expertise": None,
            "interests": [],
            "accessibility": [],
        }

    def test_simulated_failure_blocks_then_recovers(self, visitor_client):
        visitor_client.post(
            "/api/visitor/onboarding/progress", json=_progress(step="privacy")
        )
        visitor_client.post(
            "/api/admin/visitor/simulate",
            json={"scenario": "unit_unavailable"},
            headers=_admin(),
        )
        assert visitor_client.post("/api/visitor/onboarding/start").status_code == 409
        reset = visitor_client.post(
            "/api/admin/visitor/simulate",
            json={"scenario": "reset"},
            headers=_admin(),
        )
        assert reset.json()["readiness"]["ready"] is True
        assert visitor_client.post("/api/visitor/onboarding/start").status_code == 200

    def test_transfer_failure_is_atomic_and_retryable(self, visitor_client):
        visitor_client.post(
            "/api/visitor/onboarding/progress", json=_progress(step="privacy")
        )
        visitor_client.post(
            "/api/admin/visitor/simulate",
            json={"scenario": "transfer_failure"},
            headers=_admin(),
        )
        failed = visitor_client.post("/api/visitor/onboarding/start")
        assert failed.status_code == 409
        live = visitor_client.get("/api/admin/live-status", headers=_admin()).json()
        assert live["state"]["phase"] == "ready"
        assert live["state"]["transfer"] == "failed"


class TestRuntimeBridge:
    def test_runtime_bridge_transfers_coarse_profile_and_controls_session(self):
        runtime = _FakeRuntime()
        service = VisitorService(runtime_service=runtime)
        service.progress(
            VisitorProgressRequest(
                **_progress(
                    step="privacy",
                    language="fr",
                    age_guidance="13_17",
                    expertise="enthusiast",
                    interests=["technique"],
                )
            )
        )

        bootstrap = service.bootstrap()
        assert bootstrap["mode"] == "runtime"
        assert bootstrap["public_languages"] == ["en", "fr", "es", "it"]
        assert bootstrap["readiness"]["ready"] is True

        started = service.start()
        assert started["phase"] == "in_use"
        assert runtime.started == 1
        assert runtime.profile_calls == [
            {
                "language": "fr",
                "profile": "teen",
                "accessibility_mode": False,
            }
        ]

        stopped = service.stop()
        assert stopped["stopped"] is True
        assert runtime.stopped == 1

    def test_runtime_bridge_blocks_start_without_a_fresh_camera(self):
        service = VisitorService(runtime_service=_FakeRuntime(camera_ready=False))
        service.progress(VisitorProgressRequest(**_progress(step="privacy")))

        readiness = service.readiness()
        camera = next(item for item in readiness["items"] if item["id"] == "camera")
        assert camera["status"] == "unavailable"
        with pytest.raises(RuntimeError, match="Camera"):
            service.start()

    def test_runtime_bridge_blocks_preview_only_language(self):
        service = VisitorService(runtime_service=_FakeRuntime())
        service.progress(
            VisitorProgressRequest(**_progress(step="privacy", language="ar"))
        )

        language = next(
            item for item in service.readiness()["items"] if item["id"] == "language"
        )
        assert language["status"] == "unsupported"
