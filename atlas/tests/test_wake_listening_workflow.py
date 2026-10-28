"""Bounded camera-free device loops: addresses never consume the question."""

from types import SimpleNamespace

import pytest

from atlas.app.device_runtime import DeviceRuntime
from atlas.audio.stt import TranscriptResult
from atlas.config.settings import Settings
from atlas.dashboard.visitor_activation import wake_phrase_matches
from atlas.dialogue.dialogue_engine import DialogueEngine
from atlas.dialogue.mock_llm_client import MockLLMClient
from atlas.hardware.mock_hardware import MockHardware
from atlas.vision.detector import ArtworkDetection


@pytest.mark.parametrize("legacy_gate", [False, True])
@pytest.mark.parametrize("camera_online", [False, True])
@pytest.mark.parametrize("speech", [
    ["Bonjour Atlas", None, None, "euh", "Qui a peint la Joconde ?"],
    ["Hey Atlas, qui a peint la Joconde ?"],
    ["Bonjour Atlas", "Hey Atlas", "Qui a peint la Joconde ?"],
])
def test_only_explicit_wake_introduces_and_retains_the_actual_question(
    monkeypatch, speech, legacy_gate, camera_online,
):
    events = []
    speech = (["Hey Atlas"] if legacy_gate else []) + speech
    questions = iter(speech)
    service = SimpleNamespace(
        session_id="synthetic-visit", language="fr", profile="child",
        demo_active=True, wake_pending=legacy_gate,
        greeting_pending=False, greeting_completed=False,
    )
    mic = {"open": False}
    frame = object() if camera_online else None
    selected = ArtworkDetection(
        artwork_id="mona_lisa", label="Mona Lisa", confidence=0.99,
        center_score=1.0, stable=True, source="vision",
    ) if camera_online else None

    def greet():
        assert not mic["open"], "Speech must not be recorded as a new question"
        if not service.greeting_pending:
            return False
        events.append("introduction")
        service.greeting_pending = False
        service.greeting_completed = True
        return True

    def activate(text):
        if not wake_phrase_matches(text, service.language):
            return False
        events.append("wake accepted silently")
        service.wake_pending = False
        service.greeting_pending = not service.greeting_completed
        return True

    service.speak_pending_greeting = greet
    service.activate_from_wake = activate

    class Listener:
        def __init__(self, runner):
            pass

        def start(self):
            pass

        def stop(self):
            mic["open"] = False

        def activate(self):
            mic["open"] = True
            events.append("listen")

        def deactivate(self):
            mic["open"] = False

        def pop(self):
            assert mic["open"]
            text = next(questions)
            if text is not None:
                mic["open"] = False
                events.append(("heard", text))
                return TranscriptResult(text, "fr", confidence=0.9)

        def clear_prompts(self):
            pass

        def response_finished(self):
            mic["open"] = True

        def request_prompt(self, callback):
            pytest.fail("No proactive camera speech may interrupt the request")

    class Camera:
        count = 0

        def wait_for_new_frame(self, **kwargs):
            self.count += 1
            assert self.count <= 10, "Bound the synthetic device loop"
            return frame, self.count

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
            assert not mic["open"]
            assert transcript.text.casefold() == "qui a peint la joconde ?"
            assert transcript.language == "fr"
            assert transcript.confidence == 0.9
            assert kwargs["frame"] is frame
            events.append("answer")
            return SimpleNamespace(success=True, event=None, detection=None)

    container = SimpleNamespace(
        settings=Settings(), session_runner=Runner(), camera_source=Camera(),
        artwork_tracker=SimpleNamespace(
            manual_override=None, update=lambda _: selected,
        ),
        hardware=MockHardware(), dialogue_engine=DialogueEngine(MockLLMClient()),
        close=lambda: None,
    )
    runtime = DeviceRuntime(container)
    runtime._dashboard_service = service
    monkeypatch.setattr("atlas.app.device_runtime.ContinuousQuestionListener", Listener)
    class ImmediateHold:
        candidate_id = None

        def __init__(self, *args):
            pass

        def reset(self):
            self.candidate_id = None

        def observe(self, detection, **kwargs):
            self.candidate_id = detection.artwork_id if detection else None
            return detection is not None

        def held_seconds(self):
            return 5.0

    monkeypatch.setattr("atlas.app.device_runtime.VisionHold", ImmediateHold)
    monkeypatch.setattr(runtime, "preload", lambda: dict.fromkeys(
        runtime._required_components(), "ready",
    ))
    monkeypatch.setattr(runtime, "_start_dashboard", lambda: "mock")
    monkeypatch.setattr(runtime, "_start_headset_button_listener", lambda: "disabled")
    monkeypatch.setattr(runtime, "_start_terminal_capture_listener", lambda: None)
    monkeypatch.setattr(runtime, "_stop_dashboard", lambda: None)
    runtime.run(max_interactions=1)
    expected_intro = int(any(wake_phrase_matches(text or "", "fr") for text in speech))
    assert events.count("introduction") == expected_intro
    assert events[0] == "listen"
    assert events[-1] == "answer"
    if expected_intro:
        first_wake = next(index for index, event in enumerate(events)
                          if isinstance(event, tuple)
                          and wake_phrase_matches(event[1], "fr"))
        assert first_wake < events.index("introduction") < events.index("answer")
