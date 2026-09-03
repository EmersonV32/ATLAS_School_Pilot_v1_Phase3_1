"""Contract, lifecycle, privacy, and shell tests for visitor onboarding."""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

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
    def __init__(
        self,
        *,
        camera_ready: bool = True,
        camera_age_s: float | None = 0.1,
        camera_error: str | None = None,
    ) -> None:
        self.camera_ready = camera_ready
        self.camera_age_s = camera_age_s
        self.camera_error = camera_error
        self.profile_calls: list[dict] = []
        self.started = 0
        self.start_modes: list[bool] = []
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
            "camera": {
                "ready": self.camera_ready,
                "last_frame_age_s": self.camera_age_s,
                "last_error": self.camera_error,
            },
            "emergency_stopped": False,
        }

    def set_profile(self, **kwargs) -> dict:
        self.profile_calls.append(kwargs)
        return kwargs

    def start_session(self, *, demo: bool = False) -> dict:
        self.started += 1
        self.start_modes.append(demo)
        return {"session_id": "anonymous-session", "demo_active": demo}

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
        assert 'src="/static/visitor/assets/atlas-logo-v2.webp"' in response.text
        assert 'class="welcome-gallery"' in response.text
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
        assert 'id="admin-unlock-gate"' in response.text
        assert 'id="btn-start-demo"' in response.text
        assert 'id="admin-workspace"' in response.text
        assert 'class="admin-page admin-locked"' in response.text
        assert "/static/style.css?v=13" in response.text
        assert "/static/admin.js?v=15" in response.text
        assert 'id="btn-toggle-visitor-monitor"' in response.text
        assert 'id="btn-save-config-top"' in response.text
        assert 'data-log-format="human"' in response.text
        assert 'data-log-format="raw"' in response.text

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
        assert 'CACHE_NAME = "atlas-visitor-shell-v26"' in response.text
        assert '"/static/visitor.js?v=26"' in response.text
        assert '"/static/visitor/assets/atlas-logo-v2.webp"' in response.text
        assert '"/static/visitor/assets/gallery-mona-lisa.webp"' in response.text
        assert '"/static/visitor/assets/expertise-mona.webp"' in response.text
        assert '"/static/visitor/locales/fr.json"' in response.text
        assert '"/api/' not in response.text
        assert 'request.method !== "GET"' in response.text

    def test_visitor_shell_uses_the_current_service_worker_asset_version(
        self, visitor_client
    ):
        html = visitor_client.get("/").text
        assert "/static/visitor.css?v=26" in html
        assert "/static/visitor.js?v=26" in html
        assert 'rel="preload" as="image"' in html

    def test_visitor_shell_uses_artwork_led_visual_hierarchy(self):
        css = (STATIC_DIR / "visitor.css").read_text(encoding="utf-8")
        source = (STATIC_DIR / "visitor.js").read_text(encoding="utf-8")
        assert ".welcome-gallery" in css
        assert ".welcome-slide.is-active" in css
        assert "object-fit: contain" in css
        assert "aspect-ratio: 8 / 3" in css
        assert "aspect-ratio: 4 / 3" in css
        assert ".artwork-thumb img" in css
        assert "padding: clamp(0.45rem, 1vw, 0.8rem)" in css
        assert "white-space: nowrap" in css
        assert "visitor-screen-enter" in css
        assert "function startWelcomeSlideshow()" in source
        assert "startWelcomeSlideshow();" in source
        assert "function startReadinessPolling()" in source
        assert 'void refreshReadiness({ silent: true });' in source

    def test_admin_preserves_unsaved_experience_and_supports_log_views(self):
        source = (STATIC_DIR / "admin.js").read_text(encoding="utf-8")
        assert "let experienceDirty = false" in source
        assert "if (experienceDirty) return;" in source
        assert '"/logs/runtime/human"' not in source
        assert 'logFormats.runtime === "human"' in source
        assert "setVisitorMonitorCollapsed" in source

    def test_guided_log_endpoints_keep_operator_text_readable(self, visitor_client):
        runtime = visitor_client.get("/logs/runtime/human?limit=5", headers=_admin())
        events = visitor_client.get("/logs/recent/human?limit=5")
        assert runtime.status_code == 200
        assert runtime.json()["available"] is False
        assert events.status_code == 200
        assert isinstance(events.json(), list)

    def test_visitor_images_are_served_by_the_shared_dashboard_service(
        self, visitor_client
    ):
        for asset in (
            "atlas-logo-v2.webp",
            "gallery-mona-lisa.webp",
            "gallery-great-wave.webp",
            "gallery-ambassadors.webp",
            "expertise-mona.webp",
            "expertise-wave.webp",
            "expertise-ambassadors.webp",
            "interest-stories.webp",
            "flag-en.svg",
        ):
            response = visitor_client.get(f"/static/visitor/assets/{asset}")
            assert response.status_code == 200
            assert response.content

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
            if locale_name == "zh-Hant":
                assert locale["status"] == "validated"

    def test_age_is_entered_with_private_numeric_keypad(self, visitor_client):
        html = visitor_client.get("/").text
        source = (STATIC_DIR / "visitor.js").read_text(encoding="utf-8")

        assert 'id="visitor-age" type="text" readonly inputmode="none"' in html
        assert html.count('data-digit="') == 10
        assert "ageGuidance = age < 13" in source
        assert "keypadValue.length >=" not in source
        assert "5 to 120" not in html
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
        assert manifest["development_placeholders"] is False
        assert manifest["version"] == 2
        assert len(manifest["interests"]) == 6
        assert all(item["approved"] is False for item in manifest["interests"])
        expected_assets = {
            "/static/visitor/assets/interest-stories.webp",
            "/static/visitor/assets/interest-technique.webp",
            "/static/visitor/assets/interest-symbols.webp",
            "/static/visitor/assets/interest-history.webp",
            "/static/visitor/assets/interest-color-light.webp",
            "/static/visitor/assets/interest-people-society.webp",
        }
        assert {item["asset"] for item in manifest["interests"]} == expected_assets
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
        assert body["inactivity_timeout_seconds"] == 0
        assert body["public_languages"] == ["en", "fr", "es", "it", "zh-Hant"]
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

    @pytest.mark.parametrize("language", ["en", "fr", "es", "it", "zh-Hant"])
    def test_mock_readiness_accepts_all_current_speech_languages(
        self, visitor_client, language
    ):
        visitor_client.post(
            "/api/visitor/onboarding/progress",
            json=_progress(step="privacy", language=language),
        )

        language_item = next(
            item
            for item in visitor_client.get("/api/visitor/readiness").json()["items"]
            if item["id"] == "language"
        )
        assert language_item["status"] == "ready"

    def test_unknown_interest_is_rejected(self, visitor_client):
        response = visitor_client.post(
            "/api/visitor/onboarding/progress",
            json=_progress(interests=["not-in-the-approved-manifest"]),
        )
        assert response.status_code == 400

    def test_all_six_interests_can_be_selected(self, visitor_client):
        interests = [
            "stories",
            "technique",
            "symbols",
            "history",
            "color-light",
            "people-society",
        ]
        response = visitor_client.post(
            "/api/visitor/onboarding/progress",
            json=_progress(step="accessibility", interests=interests),
        )

        assert response.status_code == 200
        assert response.json()["profile"]["interests"] == interests

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
            "/api/admin/demo/start",
            json={"language": "en", "profile": "adult_beginner"},
        ).status_code == 401
        assert visitor_client.post(
            "/api/admin/visitor/simulate", json={"scenario": "ready"}
        ).status_code == 401

    def test_admin_can_start_and_restart_demo_atomically(self, visitor_client):
        payload = {
            "language": "fr",
            "profile": "expert",
            "accessibility_mode": False,
        }
        first = visitor_client.post(
            "/api/admin/demo/start", json=payload, headers=_admin()
        )
        second = visitor_client.post(
            "/api/admin/demo/start", json=payload, headers=_admin()
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["phase"] == "in_use"
        assert second.json()["language"] == "fr"
        assert second.json()["demo_mode"] is True
        source = (STATIC_DIR / "admin.js").read_text(encoding="utf-8")
        assert 'api("/api/admin/demo/start"' in source

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
        assert live["state"]["demo_mode"] is False


class TestRuntimeBridge:
    def test_runtime_bridge_refreshes_headset_after_shokz_reconnect(self, monkeypatch):
        runtime = _FakeRuntime()
        runtime.container = SimpleNamespace(
            settings=SimpleNamespace(
                hardware=SimpleNamespace(headset_name="Shokz OpenComm2")
            )
        )
        monkeypatch.setattr(
            "atlas.dashboard.visitor_service.find_pulse_playback", lambda _: None
        )
        monkeypatch.setattr(
            "atlas.dashboard.visitor_service.find_pulse_capture", lambda _: None
        )
        monkeypatch.setattr(
            "atlas.dashboard.visitor_service.find_alsa_playback", lambda _: None
        )
        service = VisitorService(runtime_service=runtime)
        initial = next(
            item for item in service.readiness()["items"] if item["id"] == "headset"
        )
        assert initial["status"] == "unavailable"

        monkeypatch.setattr(
            "atlas.dashboard.visitor_service.find_pulse_playback", lambda _: "shokz"
        )
        monkeypatch.setattr(
            "atlas.dashboard.visitor_service.find_pulse_capture", lambda _: "shokz"
        )
        monkeypatch.setattr(
            "atlas.dashboard.visitor_service.find_alsa_playback", lambda _: "plughw:1,0"
        )
        reconnected = next(
            item for item in service.readiness()["items"] if item["id"] == "headset"
        )
        assert reconnected["status"] == "ready"

    def test_runtime_bridge_supports_split_input_and_output(self, monkeypatch):
        runtime = _FakeRuntime()
        runtime.container = SimpleNamespace(
            settings=SimpleNamespace(
                hardware=SimpleNamespace(
                    headset_name="Shokz OpenComm2",
                    audio_output_name="UACDemoV1.0",
                )
            )
        )
        requested = {"playback": [], "capture": [], "alsa": []}
        monkeypatch.setattr(
            "atlas.dashboard.visitor_service.find_pulse_playback",
            lambda name: requested["playback"].append(name) or "speaker",
        )
        monkeypatch.setattr(
            "atlas.dashboard.visitor_service.find_pulse_capture",
            lambda name: requested["capture"].append(name) or "shokz",
        )
        monkeypatch.setattr(
            "atlas.dashboard.visitor_service.find_alsa_playback",
            lambda name: requested["alsa"].append(name) or "plughw:3,0",
        )

        service = VisitorService(runtime_service=runtime)
        headset = next(
            item for item in service.readiness()["items"] if item["id"] == "headset"
        )

        assert headset["status"] == "ready"
        assert requested == {
            "playback": ["UACDemoV1.0"],
            "capture": ["Shokz OpenComm2"],
            "alsa": ["UACDemoV1.0"],
        }

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
        assert bootstrap["public_languages"] == ["en", "fr", "es", "it", "zh-Hant"]
        assert bootstrap["readiness"]["ready"] is True

        started = service.start()
        assert started["phase"] == "in_use"
        assert started["demo_mode"] is True
        assert runtime.started == 1
        assert runtime.start_modes == [True]
        assert runtime.profile_calls == [
            {
                "language": "fr",
                "profile": "teen",
                "pack_id": None,
                "accessibility_mode": False,
            }
        ]

        stopped = service.stop()
        assert stopped["stopped"] is True
        assert runtime.stopped == 1

    def test_runtime_bridge_admin_demo_applies_settings_and_restarts(self):
        runtime = _FakeRuntime()
        service = VisitorService(runtime_service=runtime)

        first = service.start_demo(
            language="zh",
            profile="expert",
            pack_id="default",
            accessibility_mode=False,
        )
        second = service.start_demo(
            language="it",
            profile="adult_beginner",
            pack_id="default",
            accessibility_mode=False,
        )

        assert first["demo_mode"] is True
        assert second["language"] == "it"
        assert runtime.started == 2
        assert runtime.start_modes == [True, True]
        assert runtime.stopped == 1
        assert runtime.profile_calls[-1] == {
            "language": "it",
            "profile": "adult_beginner",
            "pack_id": "default",
            "accessibility_mode": False,
        }

    def test_admin_demo_keeps_running_session_when_readiness_is_blocked(self):
        runtime = _FakeRuntime()
        service = VisitorService(runtime_service=runtime)
        service.start_demo(language="en", profile="adult_beginner")
        runtime.camera_ready = False
        runtime.camera_age_s = None
        runtime.camera_error = "camera disconnected"

        with pytest.raises(RuntimeError, match="Camera"):
            service.start_demo(language="fr", profile="expert")

        state = service.live_status()["state"]
        assert state["phase"] == "in_use"
        assert state["language"] == "en"
        assert runtime.started == 1
        assert runtime.stopped == 0

    def test_runtime_bridge_ignores_kiosk_reset_during_active_visit(self):
        runtime = _FakeRuntime()
        service = VisitorService(runtime_service=runtime)
        service.progress(VisitorProgressRequest(**_progress(step="privacy")))
        service.start()

        reset_state = service.reset()

        assert reset_state["phase"] == "in_use"
        assert runtime.stopped == 0
        assert service.stop()["stopped"] is True
        assert runtime.stopped == 1

    def test_runtime_bridge_blocks_start_without_a_fresh_camera(self):
        service = VisitorService(runtime_service=_FakeRuntime(camera_ready=False))
        service.progress(VisitorProgressRequest(**_progress(step="privacy")))

        readiness = service.readiness()
        camera = next(item for item in readiness["items"] if item["id"] == "camera")
        assert camera["status"] == "unavailable"
        with pytest.raises(RuntimeError, match="Camera"):
            service.start()

    def test_runtime_bridge_reports_disconnected_camera_without_hiding_site(self):
        service = VisitorService(
            runtime_service=_FakeRuntime(
                camera_ready=False,
                camera_age_s=None,
                camera_error="could not open camera source",
            )
        )

        readiness = service.readiness()
        camera = next(item for item in readiness["items"] if item["id"] == "camera")

        assert camera["status"] == "unavailable"
        assert camera["detail"] == (
            "Camera disconnected. Reconnect it when ready; this website "
            "remains available."
        )

    def test_runtime_bridge_blocks_a_stale_camera_frame(self):
        service = VisitorService(runtime_service=_FakeRuntime(camera_age_s=3.1))
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
