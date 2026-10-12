"""Voice outcome telemetry contains flags only and cannot revive an old visit."""
import json
import threading
from types import SimpleNamespace

import pytest

from atlas.dashboard.runtime_service import RuntimeService


@pytest.fixture
def service():
    instance = RuntimeService.__new__(RuntimeService)
    instance._session_lock = threading.RLock()
    instance._session_generation = 1
    instance._session_changed = None
    instance._last_interaction = None
    instance.last_answer = None
    instance.session_id = "synthetic-session"
    engine = SimpleNamespace(conversation_generation=7)
    engine.reset_conversation = lambda: setattr(engine, "conversation_generation", 8)
    instance.container = SimpleNamespace(
        dialogue_engine=engine, artwork_tracker=SimpleNamespace(reset=lambda: None),
    )
    return instance


@pytest.mark.parametrize(
    ("error", "tts_ok", "expected"),
    [(None, True, "completed"), ("provider_failure", True, "failed"),
     (None, False, "failed"), ("provider_failure", False, "failed")],
)
def test_voice_outcome_is_metadata_only(service, error, tts_ok, expected):
    result = SimpleNamespace(
        dialogue=SimpleNamespace(
            error=error, response="Private synthetic answer", fallback_used=False,
        ),
        transcript=SimpleNamespace(text="Private synthetic speech"),
        error=None, tts_ok=tts_ok,
    )
    assert service.record_voice_result(
        result, session_id="synthetic-session", expected_generation=7, latency_ms=120,
    )
    outcome = service._last_interaction
    assert outcome["state"] == expected
    assert outcome["speech_ok"] == tts_ok
    assert outcome["response_failed"] == bool(error)
    assert outcome["latency_ms"] == 120
    assert "Private" not in json.dumps(outcome)
    assert "provider_failure" not in json.dumps(outcome)


@pytest.mark.parametrize(
    ("session_id", "generation", "error"),
    [("old-session", 7, None), ("synthetic-session", 6, None),
     ("synthetic-session", 7, "session_cancelled")],
)
def test_late_or_cancelled_outcome_is_ignored(service, session_id, generation, error):
    assert not service.record_voice_result(
        SimpleNamespace(error=error), session_id=session_id,
        expected_generation=generation, latency_ms=100,
    )
    assert service._last_interaction is None


def test_new_visit_clears_outcome_and_nonfinite_latency_is_not_serialized(service):
    assert service.record_voice_result(
        SimpleNamespace(error=None, dialogue=None), session_id="synthetic-session",
        expected_generation=7, latency_ms=float("nan"),
    )
    assert service._last_interaction["state"] == "control"
    assert service._last_interaction["latency_ms"] is None
    service._invalidate_session()
    assert service._last_interaction is None
