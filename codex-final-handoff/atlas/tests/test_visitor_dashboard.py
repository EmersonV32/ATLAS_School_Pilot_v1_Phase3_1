"""Contract, lifecycle, privacy, and shell tests for visitor onboarding."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from atlas.app.dependency_container import Container
from atlas.config.settings import DashboardSettings, PathsSettings, Settings
from atlas.dashboard.api import create_app

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


class TestVisitorShell:
    def test_root_is_onboarding_only(self, visitor_client):
        response = visitor_client.get("/")
        assert response.status_code == 200
        assert "Meet art with" in response.text
        assert "Start My Experience" in response.text
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
        assert '"/api/' not in response.text
        assert 'request.method !== "GET"' in response.text

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
