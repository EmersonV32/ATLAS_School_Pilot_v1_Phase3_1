"""Security and approval tests for the Codex admin operations copilot."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from atlas.app.dependency_container import Container
from atlas.config.settings import DashboardSettings, PathsSettings, Settings
from atlas.dashboard.admin_ai import OpenAIPlanner
from atlas.dashboard.api import create_app

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKS_DIR = REPO_ROOT / "data" / "content_packs"
ADMIN_TOKEN = "admin-ai-test-token"


def _headers() -> dict[str, str]:
    return {"X-Atlas-Admin-Token": ADMIN_TOKEN}


@pytest.fixture()
def app_factory(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_ADMIN_TOKEN", ADMIN_TOKEN)
    for sub in ("chroma", "sqlite", "logs"):
        (tmp_path / sub).mkdir()

    def factory(planner=None) -> TestClient:
        settings = Settings(
            paths=PathsSettings(
                data_dir=tmp_path,
                content_packs_dir=PACKS_DIR,
                chroma_dir=tmp_path / "chroma",
                sqlite_dir=tmp_path / "sqlite",
                logs_dir=tmp_path / "logs",
            ),
            dashboard=DashboardSettings(
                config_override_path=tmp_path / "dashboard_overrides.yaml"
            ),
        )
        return TestClient(create_app(Container(settings), admin_ai_planner=planner))

    return factory


def test_all_ai_routes_require_admin_token(app_factory):
    client = app_factory()
    assert client.get("/api/admin/ai/status").status_code == 401
    assert client.get("/api/admin/ai/jobs").status_code == 401
    assert (
        client.post("/api/admin/ai/jobs", json={"request": "inspect"}).status_code
        == 401
    )
    assert client.post("/api/admin/ai/jobs/nope/approve").status_code == 401
    assert client.post("/api/admin/ai/jobs/nope/reject").status_code == 401


def test_openai_planner_uses_responses_function_call_contract():
    captured: dict = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            item = type(
                "FunctionCall",
                (),
                {
                    "type": "function_call",
                    "name": "inspect_system",
                    "arguments": json.dumps({"focus": "camera"}),
                },
            )()
            return type("Response", (), {"output": [item]})()

    planner = OpenAIPlanner.__new__(OpenAIPlanner)
    planner._client = type("Client", (), {"responses": FakeResponses()})()
    planner._model = "gpt-5.3-codex"
    action, payload = planner("Inspect the camera", {"health": {"camera": "ok"}})

    assert action == "inspect_system"
    assert payload == {"focus": "camera"}
    assert captured["model"] == "gpt-5.3-codex"
    assert captured["tool_choice"] == "required"
    assert all(tool["type"] == "function" for tool in captured["tools"])


def test_disabled_ai_reports_safe_configuration_message(app_factory):
    client = app_factory()
    response = client.get("/api/admin/ai/status", headers=_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["mode"] == "proposal_and_approval"
    assert "ATLAS_ADMIN_AI_ENABLED" in body["detail"]
    assert "OPENAI_API_KEY" not in json.dumps(body)


def test_read_only_inspection_completes_without_approval(app_factory):
    seen: dict = {}

    def planner(request, snapshot):
        seen["request"] = request
        seen["snapshot"] = snapshot
        return "inspect_system", {"focus": "camera and retrieval"}

    client = app_factory(planner)
    response = client.post(
        "/api/admin/ai/jobs",
        headers=_headers(),
        json={"request": "Please inspect camera and retrieval health"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["requires_approval"] is False
    assert body["result"]["snapshot"]["health"]
    assert seen["request"].startswith("Please inspect")
    assert "editable_config" in seen["snapshot"]


def test_mutation_waits_for_approval_and_approval_is_idempotent(app_factory):
    def planner(_request, _snapshot):
        return "reindex_content", {
            "pack_id": "demo_pack",
            "reset": True,
            "reason": "Refresh the reviewed content index.",
        }

    client = app_factory(planner)
    calls: list[tuple[str, bool]] = []
    client.app.state.service.ingest_pack = lambda pack_id, reset: (
        calls.append((pack_id, reset)) or {"chunks_ingested": 17}
    )

    proposed = client.post(
        "/api/admin/ai/jobs",
        headers=_headers(),
        json={"request": "Re-index the demo content"},
    ).json()
    assert proposed["status"] == "pending_approval"
    assert calls == []

    route = f"/api/admin/ai/jobs/{proposed['job_id']}/approve"
    approved = client.post(route, headers=_headers())
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"
    assert calls == [("demo_pack", True)]

    repeated = client.post(route, headers=_headers())
    assert repeated.status_code == 200
    assert calls == [("demo_pack", True)]


def test_rejected_mutation_never_executes(app_factory):
    def planner(_request, _snapshot):
        return "reindex_content", {
            "pack_id": "demo_pack",
            "reset": True,
            "reason": "Requested by operator.",
        }

    client = app_factory(planner)
    calls: list[str] = []
    client.app.state.service.ingest_pack = lambda pack_id, _reset: calls.append(pack_id)
    job = client.post(
        "/api/admin/ai/jobs",
        headers=_headers(),
        json={"request": "Re-index content"},
    ).json()
    rejected = client.post(
        f"/api/admin/ai/jobs/{job['job_id']}/reject", headers=_headers()
    )
    assert rejected.json()["status"] == "rejected"
    assert calls == []


def test_config_patch_is_schema_validated_before_approval(app_factory):
    def bad_planner(_request, _snapshot):
        return "update_dashboard_config", {
            "patch_json": json.dumps({"speech": {"api_key": "forbidden"}}),
            "reason": "bad",
        }

    client = app_factory(bad_planner)
    response = client.post(
        "/api/admin/ai/jobs",
        headers=_headers(),
        json={"request": "Change speech configuration"},
    )
    assert response.status_code == 400
    assert "invalid dashboard configuration" in response.json()["detail"]


def test_artwork_intake_creates_only_an_unpublished_draft(app_factory, tmp_path):
    def planner(_request, _snapshot):
        return "prepare_artwork_draft", {
            "pack_id": "demo_pack",
            "artwork_id": "test_artwork",
            "title": "Test Artwork",
            "artist": "Museum Artist",
            "source_url": "https://museum.example/artworks/test",
            "source_title": "Museum collection record",
            "notes": "Prepare content for human review.",
        }

    client = app_factory(planner)
    job = client.post(
        "/api/admin/ai/jobs",
        headers=_headers(),
        json={"request": "Prepare a draft for Test Artwork"},
    ).json()
    assert job["status"] == "pending_approval"
    assert not (tmp_path / "admin_ai_drafts").exists()

    approved = client.post(
        f"/api/admin/ai/jobs/{job['job_id']}/approve", headers=_headers()
    ).json()
    assert approved["status"] == "completed"
    assert approved["result"]["published"] is False
    assert approved["result"]["vision_model_updated"] is False
    draft_path = Path(approved["result"]["draft_file"])
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    assert draft["status"] == "unverified_draft"
    assert "Human source and copyright review" in draft["required_next_steps"]


def test_secret_values_are_rejected_and_never_logged(app_factory, tmp_path):
    calls: list[str] = []

    def planner(request, _snapshot):
        calls.append(request)
        return "respond", {"message": "ok"}

    client = app_factory(planner)
    secret = "unit-test-private-value"
    response = client.post(
        "/api/admin/ai/jobs",
        headers=_headers(),
        json={"request": f"Use password={secret}"},
    )
    assert response.status_code == 400
    assert calls == []
    log_text = "".join(
        path.read_text(encoding="utf-8") for path in (tmp_path / "logs").glob("*.jsonl")
    )
    assert secret not in log_text


def test_code_change_becomes_handoff_not_execution(app_factory):
    def planner(_request, _snapshot):
        return "propose_code_change", {
            "summary": "Add a new protected maintenance endpoint",
            "acceptance_criteria": "Feature branch, focused tests, full tests, review.",
        }

    client = app_factory(planner)
    job = client.post(
        "/api/admin/ai/jobs",
        headers=_headers(),
        json={"request": "Change the application code"},
    ).json()
    assert job["status"] == "handoff_required"
    assert "feature branch" in job["result"]["message"]
    assert job["requires_approval"] is False
