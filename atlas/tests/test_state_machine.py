"""Phase 1 tests for the interaction state machine."""

from __future__ import annotations

import pytest

from atlas.app.events import Event, State
from atlas.app.state_machine import InvalidTransition, StateMachine


def _sm() -> StateMachine:
    # No logger needed for transition logic tests.
    return StateMachine(session_id="sess_test", logger=None)


def test_happy_path_full_cycle() -> None:
    sm = _sm()
    assert sm.state is State.IDLE
    assert sm.fire(Event.START_LISTENING) is State.LISTENING
    assert sm.fire(Event.AUDIO_CAPTURED) is State.TRANSCRIBING
    assert sm.fire(Event.TRANSCRIBED) is State.DETECTING_ARTWORK
    assert sm.fire(Event.ARTWORK_DETECTED) is State.RETRIEVING
    assert sm.fire(Event.RETRIEVED) is State.GENERATING
    assert sm.fire(Event.GENERATED) is State.VALIDATING
    assert sm.fire(Event.VALIDATION_PASSED) is State.SPEAKING
    assert sm.fire(Event.SPOKEN) is State.WAITING_FOR_FOLLOWUP
    assert sm.fire(Event.FOLLOWUP_TIMEOUT) is State.IDLE


def test_followup_loops_back_to_listening() -> None:
    sm = _sm()
    for ev in (
        Event.START_LISTENING,
        Event.AUDIO_CAPTURED,
        Event.TRANSCRIBED,
        Event.ARTWORK_DETECTED,
        Event.RETRIEVED,
        Event.GENERATED,
        Event.VALIDATION_PASSED,
        Event.SPOKEN,
    ):
        sm.fire(ev)
    assert sm.state is State.WAITING_FOR_FOLLOWUP
    assert sm.fire(Event.FOLLOWUP_RECEIVED) is State.LISTENING


def test_validation_retry_returns_to_generating() -> None:
    sm = _sm()
    for ev in (
        Event.START_LISTENING,
        Event.AUDIO_CAPTURED,
        Event.TRANSCRIBED,
        Event.ARTWORK_DETECTED,
        Event.RETRIEVED,
        Event.GENERATED,
    ):
        sm.fire(ev)
    assert sm.state is State.VALIDATING
    assert sm.fire(Event.VALIDATION_FAILED_RETRY) is State.GENERATING


def test_validation_fallback_goes_to_speaking() -> None:
    sm = _sm()
    for ev in (
        Event.START_LISTENING,
        Event.AUDIO_CAPTURED,
        Event.TRANSCRIBED,
        Event.ARTWORK_DETECTED,
        Event.RETRIEVED,
        Event.GENERATED,
    ):
        sm.fire(ev)
    assert sm.fire(Event.VALIDATION_FAILED_FALLBACK) is State.SPEAKING


def test_illegal_transition_raises() -> None:
    sm = _sm()
    with pytest.raises(InvalidTransition):
        sm.fire(Event.RETRIEVED)  # not valid from IDLE


def test_error_reachable_from_any_state() -> None:
    sm = _sm()
    sm.fire(Event.START_LISTENING)
    assert sm.fire(Event.ERROR_OCCURRED, error_type="stt_timeout") is State.ERROR
    # cannot error again from ERROR
    with pytest.raises(InvalidTransition):
        sm.fire(Event.ERROR_OCCURRED)


def test_reset_from_error_returns_idle() -> None:
    sm = _sm()
    sm.fire(Event.START_LISTENING)
    sm.fire(Event.ERROR_OCCURRED)
    assert sm.state is State.ERROR
    assert sm.reset() is State.IDLE


def test_can_predicate() -> None:
    sm = _sm()
    assert sm.can(Event.START_LISTENING) is True
    assert sm.can(Event.SPOKEN) is False
    assert sm.can(Event.ERROR_OCCURRED) is True
