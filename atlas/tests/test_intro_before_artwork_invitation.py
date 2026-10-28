"""A demo camera prompt cannot replace the visitor's explicit introduction."""

from types import SimpleNamespace

import pytest

from atlas.app.device_runtime import DeviceRuntime
from atlas.config.settings import Settings
from atlas.dashboard.runtime_service import RuntimeService
from atlas.dialogue.dialogue_engine import DialogueEngine
from atlas.dialogue.mock_llm_client import MockLLMClient
from atlas.hardware.mock_hardware import MockHardware
from atlas.vision.detector import ArtworkDetection


class SpeechRecorder:
    def __init__(self, succeeds=True):
        self.succeeds = succeeds
        self.events = []

    def speak(self, text, language):
        self.events.append(("public", text, language))
        return self.succeeds

    def speak_private_local(self, text, language):
        self.events.append(("private", text, language))
        return self.succeeds


def make_visit(name, succeeds=True):
    speech = SpeechRecorder(succeeds)
    container = SimpleNamespace(
        settings=Settings(),
        hardware=MockHardware(),
        dialogue_engine=DialogueEngine(MockLLMClient()),
        artwork_tracker=SimpleNamespace(
            reset=lambda: None,
            manual_override=None,
        ),
        tts=speech,
        logger=SimpleNamespace(log=lambda **_kw: None),
        close=lambda: None,
    )
    service = RuntimeService(container)
    service.language = "fr"
    service.start_session(demo=True, wake_required=False, greeting_name=name)
    return container, service, speech


@pytest.mark.parametrize("name", [None, "Emerson"])
def test_completed_intro_requires_successful_explicit_wake_and_current_visit(name):
    _container, service, speech = make_visit(name)
    assert not service.wake_pending
    assert not service.introduction_completed
    assert not service.activate_from_wake("Salut Atlas")
    assert not service.introduction_completed
    assert not speech.events
    assert service.activate_from_wake("Bonjour Atlas")
    assert not service.introduction_completed
    assert service.speak_pending_greeting()
    assert service.introduction_completed
    assert len(speech.events) == 1
    assert speech.events[0][0] == ("private" if name else "public")
    service.stop_session()
    assert not service.introduction_completed
    service.start_session(demo=True, wake_required=False, greeting_name=name)
    assert not service.introduction_completed


@pytest.mark.parametrize("name", [None, "Emerson"])
def test_failed_or_cancelled_intro_does_not_enable_proactive_speech(name):
    _container, service, speech = make_visit(name, succeeds=False)
    assert service.activate_from_wake("Hey Atlas")
    assert not service.speak_pending_greeting()
    assert not service.introduction_completed
    assert not service.wake_pending
    speech.succeeds = True
    assert service.activate_from_wake("Bonjour Atlas")
    speech.speak = lambda *_args: service.stop_session() or True
    speech.speak_private_local = speech.speak
    assert not service.speak_pending_greeting()
    assert not service.introduction_completed


@pytest.mark.parametrize("name", [None, "Emerson"])
@pytest.mark.parametrize("intro", ["not_requested", "failed", "completed"])
@pytest.mark.parametrize("path", ["stable_camera", "manual_capture"])
def test_both_demo_camera_paths_wait_for_successful_introduction(
    monkeypatch, name, intro, path
):
    container, service, speech = make_visit(name, succeeds=intro != "failed")
    if intro != "not_requested":
        assert service.activate_from_wake("Hey Atlas")
        assert service.speak_pending_greeting() == (intro == "completed")
    assert not service.wake_pending, "Match the visitor dashboard's ungated mode"
    before = len(speech.events)
    callbacks = []
    selected = ArtworkDetection(
        artwork_id="mona_lisa",
        label="La Joconde",
        confidence=0.99,
        center_score=1.0,
        stable=True,
        source="vision",
    )

    class FinishedLoop(Exception):
        pass

    class Camera:
        count = 0

        def wait_for_new_frame(self, **_kwargs):
            self.count += 1
            if self.count > 3:
                raise FinishedLoop
            return object(), self.count

    class Runner:
        def set_preferred_language(self, _value):
            pass

        def set_preferred_profile(self, _value):
            pass

        def set_preferred_accessibility(self, _value):
            pass

        def cue_listening(self):
            pass

        def capture_context(self, *_args, **_kwargs):
            return SimpleNamespace(success=True, detection=selected)

        def invite_about_artwork(self, _detection, language):
            return speech.speak("Voulez-vous en savoir plus sur La Joconde ?", language)

    class Listener:
        def __init__(self, _runner):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        def activate(self):
            pass

        def request_prompt(self, callback):
            callbacks.append(callback)
            callback()

        def pop(self):
            return None

    class ImmediateHold:
        candidate_id = None

        def __init__(self, *_args):
            pass

        def reset(self):
            self.candidate_id = None

        def observe(self, detection, **_kwargs):
            self.candidate_id = detection.artwork_id
            return True

        def held_seconds(self):
            return 5.0

    container.session_runner = Runner()
    container.camera_source = Camera()
    container.artwork_tracker.update = lambda _frame: selected
    runtime = DeviceRuntime(container)
    runtime._dashboard_service = service
    if path == "manual_capture":
        runtime._capture_requested.set()
    monkeypatch.setattr("atlas.app.device_runtime.ContinuousQuestionListener", Listener)
    monkeypatch.setattr("atlas.app.device_runtime.VisionHold", ImmediateHold)
    monkeypatch.setattr("atlas.app.device_runtime.time.sleep", lambda _seconds: None)
    monkeypatch.setattr(runtime, "_check_dashboard_port_available", lambda: None)
    monkeypatch.setattr(
        runtime,
        "preload",
        lambda: dict.fromkeys(
            runtime._required_components(),
            "ready",
        ),
    )
    monkeypatch.setattr(runtime, "_start_dashboard", lambda: "mock")
    monkeypatch.setattr(runtime, "_start_headset_button_listener", lambda: "disabled")
    monkeypatch.setattr(runtime, "_start_terminal_capture_listener", lambda: None)
    monkeypatch.setattr(runtime, "_stop_dashboard", lambda: None)
    with pytest.raises(FinishedLoop):
        runtime.run()
    expected = int(intro == "completed")
    assert len(callbacks) == expected
    assert len(speech.events) - before == expected
    if expected:
        # A deferred camera prompt cannot survive stop/restart, even if the
        # replacement visit has already completed its own introduction.
        service.stop_session()
        service.start_session(demo=True, wake_required=False)
        assert service.activate_from_wake("Bonjour Atlas")
        assert service.speak_pending_greeting()
        after_restart = len(speech.events)
        assert callbacks[0]() is False
        assert len(speech.events) == after_restart
