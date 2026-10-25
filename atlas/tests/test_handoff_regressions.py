"""Regression checks for the October handoff's security/recovery failures."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from atlas.app.dependency_container import Container
from atlas.app.device_runtime import ContinuousQuestionListener, DeviceRuntime
from atlas.audio.mock_stt import MockSTT
from atlas.audio.mock_tts import MockTTS
from atlas.audio.stt import TranscriptResult
from atlas.config.settings import PathsSettings, Settings
from atlas.dashboard.api import create_app
from atlas.dialogue.dialogue_engine import DialogueEngine
from atlas.dialogue.mock_llm_client import MockLLMClient
from atlas.hardware.mock_hardware import MockHardware
from atlas.pipeline.session_runner import SessionRunner
from atlas.vision.detector import ArtworkDetection
from atlas.vision.mock_detector import MockDetector
from atlas.vision.tracker import ArtworkTracker

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated_app(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_ADMIN_TOKEN", "regression-admin")
    container = Container(
        Settings(
            paths=PathsSettings(
                data_dir=tmp_path,
                content_packs_dir=ROOT / "data/content_packs",
                chroma_dir=tmp_path / "chroma",
                sqlite_dir=tmp_path / "sqlite",
                logs_dir=tmp_path / "logs",
            )
        )
    )
    app = create_app(container)
    with TestClient(app) as client:
        yield client, app.state.service
    container.close()


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/status", None),
        ("GET", "/camera/frame.jpg", None),
        ("GET", "/logs/recent", None),
        ("GET", "/logs/recent/human", None),
        ("POST", "/session/start", None),
        ("POST", "/session/stop", None),
        ("POST", "/session/profile", {"language": "fr"}),
        ("POST", "/session/manual-artwork", {"artwork_id": "mona_lisa"}),
        ("DELETE", "/session/manual-artwork", None),
        ("POST", "/session/capture", None),
        ("POST", "/ask", {"question": "Hello"}),
    ],
)
@pytest.mark.parametrize("token", [None, "wrong-token"])
def test_operator_routes_reject_unauthorized_requests(
    isolated_app, method, path, body, token
):
    client, service = isolated_app
    headers = {} if token is None else {"X-Atlas-Admin-Token": token}
    assert client.request(method, path, json=body, headers=headers).status_code == 401
    assert service.session_id is None
    assert service.last_answer is None
    assert service.language == "en"


def test_camera_preview_still_works_for_authenticated_admin(isolated_app, monkeypatch):
    client, service = isolated_app
    monkeypatch.setattr(service, "camera_frame_jpeg", lambda: b"synthetic-jpeg")
    response = client.get(
        "/camera/frame.jpg", headers={"X-Atlas-Admin-Token": "regression-admin"}
    )
    assert response.status_code == 200
    assert response.content == b"synthetic-jpeg"
    assert "no-store" in response.headers["cache-control"]


@pytest.mark.parametrize("streaming", [False, True])
def test_reset_cancels_inflight_generation_without_repopulating_memory(streaming):
    started, release = threading.Event(), threading.Event()

    class DelayedLLM:
        def generate(self, messages):
            started.set()
            assert release.wait(3)
            return "Previous visitor answer."

        def generate_stream(self, messages):
            yield self.generate(messages)

    engine = DialogueEngine(DelayedLLM())
    spoken, results = [], []
    kwargs = dict(question="Previous question", artwork_chunks=[])
    call = (
        (lambda: engine.respond_stream(**kwargs, on_sentence=spoken.append))
        if streaming
        else (lambda: engine.respond(**kwargs))
    )
    thread = threading.Thread(target=lambda: results.append(call()))
    thread.start()
    assert started.wait(3)
    engine.reset_conversation()
    release.set()
    thread.join(3)
    assert not thread.is_alive()
    assert engine._conversation_turns == []
    assert results[0].error == "session_cancelled"
    assert results[0].response == ""
    assert spoken == []


def test_session_boundary_clears_answer_and_manual_context(isolated_app):
    _, service = isolated_app
    service.start_session()
    service.set_manual_artwork("mona_lisa")
    service.last_answer = {"answer": "Previous visitor"}
    service.stop_session()
    service.start_session()
    assert service.last_answer is None
    assert service.artwork_status()["artwork_id"] is None


def test_inflight_detection_cannot_repopulate_context_after_reset():
    started, release = threading.Event(), threading.Event()

    class DelayedDetector:
        def detect(self, frame):
            started.set()
            assert release.wait(3)
            return ArtworkDetection(
                artwork_id="mona_lisa", label="Mona Lisa", confidence=1
            )

    tracker = ArtworkTracker(DelayedDetector(), stability_frames=1)
    detections = []
    thread = threading.Thread(target=lambda: detections.append(tracker.update()))
    thread.start()
    assert started.wait(3)
    tracker.reset()
    release.set()
    thread.join(3)
    assert not thread.is_alive()
    assert detections == [None]
    assert tracker.last_stable is None
    assert tracker.status()["artwork_id"] is None


@pytest.mark.parametrize("stage", ["retrieval", "generation"])
def test_typed_request_cannot_publish_into_next_session(isolated_app, stage):
    client, service = isolated_app
    started, release = threading.Event(), threading.Event()

    def pause():
        started.set()
        assert release.wait(3)

    class DelayedLLM:
        def generate(self, messages):
            if stage == "generation":
                pause()
            return "A previous visitor's answer."

    def retrieve(query):
        if stage == "retrieval":
            pause()
        return SimpleNamespace(chunks=[], total_latency_ms=0)

    service.container._dialogue_engine = DialogueEngine(DelayedLLM())
    service.container._retriever = SimpleNamespace(retrieve=retrieve)
    service.start_session()
    responses = []
    thread = threading.Thread(
        target=lambda: responses.append(
            client.post(
                "/ask",
                json={"question": "Compare the arrangement of these works."},
                headers={"X-Atlas-Admin-Token": "regression-admin"},
            )
        )
    )
    thread.start()
    assert started.wait(3)
    service.stop_session()
    service.start_session()
    release.set()
    thread.join(3)
    assert not thread.is_alive()
    assert responses[0].status_code == 409
    assert service.last_answer is None
    assert service.container.dialogue_engine._conversation_turns == []


@pytest.mark.parametrize("streaming", [False, True])
def test_cancelled_voice_response_is_not_spoken(streaming):
    started, release = threading.Event(), threading.Event()

    class DelayedLLM:
        def generate(self, messages):
            started.set()
            assert release.wait(3)
            return "Old answer."

        def generate_stream(self, messages):
            yield self.generate(messages)

    engine, tts = DialogueEngine(DelayedLLM()), MockTTS()
    spoken = []
    tts.speak = lambda *args, **kwargs: spoken.append(args[0]) or True
    runner = SessionRunner(
        detector=MockDetector(),
        stt=MockSTT(),
        tts=tts,
        hardware=MockHardware(),
        dialogue_engine=engine,
        retriever=lambda *args: [],
        stream_responses=streaming,
    )
    results = []
    thread = threading.Thread(
        target=lambda: results.append(
            runner.respond_to_transcript(
                TranscriptResult(
                    text="Compare the arrangement of these works.", language="en"
                ),
            )
        )
    )
    thread.start()
    assert started.wait(3)
    engine.reset_conversation()
    release.set()
    thread.join(3)
    assert not thread.is_alive()
    assert results[0].error == "session_cancelled"
    assert spoken == []


@pytest.mark.parametrize("scenario", ["voice", "voice_manual", "demo_voice", "stop"])
def test_device_loop_handles_voice_and_session_stop_without_camera(
    monkeypatch, scenario
):
    service = SimpleNamespace(
        session_id="visit-1",
        language="en",
        profile="adult_beginner",
        demo_active=scenario == "demo_voice",
        wake_pending=False,
    )
    states = {"active": False, "answered": False, "deactivated": 0}
    selected = (
        ArtworkDetection(
            artwork_id="mona_lisa", label="Mona Lisa", confidence=1.0,
            source="manual_override", stable=True,
        ) if scenario == "voice_manual" else None
    )

    class Listener:
        def __init__(self, runner):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        def activate(self):
            states["active"] = True

        def deactivate(self):
            states["active"] = False
            states["deactivated"] += 1

        def pop(self):
            if scenario != "stop" and states["active"]:
                return TranscriptResult(text="What is composition?", language="en")

        def clear_prompts(self):
            pass

        def response_finished(self):
            pass

    class Camera:
        calls = 0

        def wait_for_new_frame(self, **kwargs):
            self.calls += 1
            if self.calls == 2 and scenario == "stop":
                service.session_id = None
            if self.calls > 3:
                raise StopIteration("bounded fake camera loop")
            return None, self.calls

        def status(self):
            return {"ready": False, "last_error": "synthetic outage"}

    class Runner:
        def set_preferred_language(self, value):
            pass

        def set_preferred_profile(self, value):
            pass

        def set_preferred_accessibility(self, value):
            pass

        def cue_listening(self):
            pass

        def respond_to_transcript(self, transcript, **kwargs):
            assert kwargs["frame"] is None
            assert kwargs["detection"] is selected
            states["answered"] = True
            return SimpleNamespace(event=None, success=True, detection=None)

    container = SimpleNamespace(
        settings=Settings(),
        artwork_tracker=SimpleNamespace(manual_override=selected),
        session_runner=Runner(),
        camera_source=Camera(),
        hardware=MockHardware(),
        dialogue_engine=DialogueEngine(MockLLMClient()),
        close=lambda: None,
    )
    runtime = DeviceRuntime(container)
    runtime._dashboard_service = service
    monkeypatch.setattr("atlas.app.device_runtime.ContinuousQuestionListener", Listener)
    monkeypatch.setattr(
        runtime,
        "preload",
        lambda: dict.fromkeys(runtime._required_components(), "ready"),
    )
    monkeypatch.setattr(runtime, "_start_dashboard", lambda: "mock")
    monkeypatch.setattr(runtime, "_start_headset_button_listener", lambda: "disabled")
    monkeypatch.setattr(runtime, "_start_terminal_capture_listener", lambda: None)
    monkeypatch.setattr(runtime, "_stop_dashboard", lambda: None)
    if scenario != "stop":
        runtime.run(max_interactions=1)
        assert states["answered"]
    else:
        with pytest.raises(StopIteration):
            runtime.run()
        assert states["deactivated"] >= 1
        assert not states["active"]


def test_listener_discards_recording_from_previous_session():
    started, release = threading.Event(), threading.Event()

    class DelayedRunner:
        def __init__(self):
            self.calls = 0

        def listen_once(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                started.set()
                assert release.wait(3)
                return TranscriptResult(text="Old visitor", language="en")
            time.sleep(0.01)
            return None

    listener = ContinuousQuestionListener(DelayedRunner())
    listener.start()
    try:
        listener.activate()
        assert started.wait(3)
        listener.deactivate()
        listener.activate()
        release.set()
        time.sleep(0.1)
        assert listener.pop() is None
    finally:
        release.set()
        listener.stop()


def bash_executable():
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    candidate = str(git_bash) if git_bash.exists() else shutil.which("bash")
    if candidate is None:
        pytest.skip("Bash is required for shell recovery/deployment checks")
    return candidate


@pytest.mark.parametrize("line_ending", ["\n", "\r\n"])
def test_restore_models_uses_release_manifest_and_rejects_corruption(
    tmp_path, line_ending
):
    scripts, models = tmp_path / "scripts", tmp_path / "models"
    scripts.mkdir()
    models.mkdir()
    script = scripts / "restore_models.sh"
    script.write_text(
        (ROOT / "scripts/restore_models.sh").read_text(), encoding="utf-8", newline="\n"
    )
    model = models / "atlas_yolo.pt"
    model.write_bytes(b"portable test checkpoint")
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    (models / "manifest.sha256").write_text(
        f"{digest}  atlas_yolo.pt{line_ending}", encoding="utf-8", newline="\n"
    )
    command = [
        bash_executable(),
        "-c",
        'export PATH="/usr/bin:/bin:$PATH"; exec bash "$@"',
        "atlas-test",
        script.as_posix(),
        "--verify-only",
    ]
    verified = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert verified.returncode == 0, verified.stdout + verified.stderr
    model.write_bytes(b"corrupt checkpoint")
    corrupt = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert corrupt.returncode != 0
