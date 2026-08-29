"""Privacy tests: defaults, log hygiene, and protected endpoints."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from atlas.app.dependency_container import Container
from atlas.config.settings import PathsSettings, Settings
from atlas.dashboard.api import create_app

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKS_DIR = REPO_ROOT / "data" / "content_packs"

FORBIDDEN_LOG_KEYS = {
    "audio", "raw_audio", "image", "raw_image", "video", "frame",
    "face", "face_data", "name", "student_name",
    "api_key", "gemini_api_key", "token", "secret", "password",
    "prompt", "system_prompt",
}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_ADMIN_TOKEN", "privacy-test-token")
    for sub in ("chroma", "sqlite", "logs"):
        (tmp_path / sub).mkdir()
    settings = Settings(
        paths=PathsSettings(
            data_dir=tmp_path,
            content_packs_dir=PACKS_DIR,
            chroma_dir=tmp_path / "chroma",
            sqlite_dir=tmp_path / "sqlite",
            logs_dir=tmp_path / "logs",
        )
    )
    container = Container(settings)
    from atlas.rag.ingest import ingest_pack

    ingest_pack(settings, PACKS_DIR / "demo_pack", reset=True)
    return TestClient(create_app(container)), tmp_path


class TestPrivacyDefaults:
    def test_settings_defaults_are_safe(self):
        s = Settings()
        assert s.privacy.store_raw_audio is False
        assert s.privacy.store_raw_images is False
        assert s.privacy.store_face_data is False
        assert s.privacy.student_names_required is False
        assert s.privacy.anonymous_session_ids is True
        assert s.privacy.session_memory_persistent is False
        assert s.logging.log_transcripts is False
        assert s.llm.cloud_llm_enabled is False

    def test_repo_config_keeps_safe_defaults(self):
        """The checked-in config/settings.yaml must not weaken privacy."""
        from atlas.config.loader import load_settings

        s = load_settings(REPO_ROOT / "config")
        assert s.privacy.store_raw_audio is False
        assert s.privacy.store_raw_images is False
        assert s.privacy.store_face_data is False
        assert s.logging.log_transcripts is False


class TestLogHygiene:
    def test_logs_have_no_forbidden_keys_or_transcripts(self, env):
        client, tmp_path = env
        client.post("/session/start")
        client.post("/session/manual-artwork", json={"artwork_id": "mona_lisa"})
        client.post("/ask", json={"question": "Who painted this secret thing?"})
        client.post("/session/stop")

        records = []
        for log_file in (tmp_path / "logs").glob("*.jsonl"):
            for line in log_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    records.append(json.loads(line))
        assert records, "expected telemetry records to be written"
        for record in records:
            keys = {k.lower() for k in record}
            assert not (keys & FORBIDDEN_LOG_KEYS), f"forbidden key in {record}"
            # transcript logging is off by default
            assert "transcript" not in record

    def test_logs_recent_endpoint_is_safe(self, env):
        client, _ = env
        client.post("/ask", json={"question": "Who painted the Mona Lisa?"})
        logs = client.get("/logs/recent").json()
        for record in logs:
            keys = {k.lower() for k in record}
            assert not (keys & FORBIDDEN_LOG_KEYS)

    def test_event_logger_drops_blocked_keys(self, tmp_path):
        from atlas.config.settings import LoggingSettings
        from atlas.storage.event_logger import EventLogger

        logger = EventLogger(tmp_path, LoggingSettings())
        event = logger.log(
            session_id="s1",
            state="test",
            event="blocklist",
            api_key="SHOULD-NOT-APPEAR",
            student_name="SHOULD-NOT-APPEAR",
            raw_audio="SHOULD-NOT-APPEAR",
            prompt="SHOULD-NOT-APPEAR",
        )
        dumped = event.model_dump()
        text = json.dumps(dumped)
        assert "SHOULD-NOT-APPEAR" not in text


class TestProtectedEndpoints:
    def test_admin_endpoints_reject_missing_token(self, env):
        client, _ = env
        ingest = client.post("/content/ingest", json={"pack_id": "demo_pack"})
        assert ingest.status_code == 401
        assert client.post("/eval/rag").status_code == 401
        assert client.post("/hardware/clear-emergency-stop").status_code == 401
        simulate = client.post("/demo/simulate", json={"scenario": "reset"})
        assert simulate.status_code == 401

    def test_admin_endpoints_disabled_without_env(self, env, monkeypatch):
        client, _ = env
        monkeypatch.delenv("ATLAS_ADMIN_TOKEN", raising=False)
        res = client.post(
            "/eval/rag", headers={"X-Atlas-Admin-Token": "anything"}
        )
        assert res.status_code == 503
