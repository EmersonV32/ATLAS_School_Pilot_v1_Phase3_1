"""The ATLAS interaction state machine.

Transitions are explicit and table-driven. Every transition is logged with
timestamp, session_id, state, event, and the latency spent in the state we
just left. ERROR is reachable from any non-terminal state via
ERROR_OCCURRED, and RESET returns to IDLE.

This module owns control flow only. It does not call vision, audio, RAG, or
the LLM directly; the orchestrator (answer pipeline, later phases) fires
events and the machine decides whether the move is legal.
"""

from __future__ import annotations

from atlas.app.events import Event, State
from atlas.storage.event_logger import EventLogger
from atlas.utils.time import now_ms

# Allowed transitions: (current_state, event) -> next_state
_TRANSITIONS: dict[tuple[State, Event], State] = {
    (State.IDLE, Event.START_LISTENING): State.LISTENING,
    (State.LISTENING, Event.AUDIO_CAPTURED): State.TRANSCRIBING,
    (State.TRANSCRIBING, Event.TRANSCRIBED): State.DETECTING_ARTWORK,
    (State.DETECTING_ARTWORK, Event.ARTWORK_DETECTED): State.RETRIEVING,
    (State.RETRIEVING, Event.RETRIEVED): State.GENERATING,
    (State.GENERATING, Event.GENERATED): State.VALIDATING,
    (State.VALIDATING, Event.VALIDATION_PASSED): State.SPEAKING,
    (State.VALIDATING, Event.VALIDATION_FAILED_RETRY): State.GENERATING,
    (State.VALIDATING, Event.VALIDATION_FAILED_FALLBACK): State.SPEAKING,
    (State.SPEAKING, Event.SPOKEN): State.WAITING_FOR_FOLLOWUP,
    (State.WAITING_FOR_FOLLOWUP, Event.FOLLOWUP_RECEIVED): State.LISTENING,
    (State.WAITING_FOR_FOLLOWUP, Event.FOLLOWUP_TIMEOUT): State.IDLE,
    (State.ERROR, Event.RESET): State.IDLE,
    (State.IDLE, Event.RESET): State.IDLE,
}


class InvalidTransition(Exception):
    """Raised when an event is not legal from the current state."""

    def __init__(self, state: State, event: Event) -> None:
        super().__init__(f"no transition from {state.value} on {event.value}")
        self.state = state
        self.event = event


class StateMachine:
    """Explicit, logged interaction state machine."""

    def __init__(
        self,
        session_id: str,
        logger: EventLogger | None = None,
        *,
        initial: State = State.IDLE,
    ) -> None:
        self.session_id = session_id
        self.logger = logger
        self.state = initial
        self._entered_ms = now_ms()

    def can(self, event: Event) -> bool:
        """Return True if `event` is legal now (ERROR_OCCURRED always is)."""
        if event is Event.ERROR_OCCURRED:
            return self.state is not State.ERROR
        return (self.state, event) in _TRANSITIONS

    def fire(
        self,
        event: Event,
        *,
        latency_ms: float | None = None,
        error_type: str | None = None,
        **log_fields: object,
    ) -> State:
        """Apply an event, returning the new state.

        Raises InvalidTransition if the move is illegal. ERROR_OCCURRED is a
        universal escape hatch from any non-error state.
        """
        if event is Event.ERROR_OCCURRED:
            if self.state is State.ERROR:
                raise InvalidTransition(self.state, event)
            next_state = State.ERROR
        else:
            try:
                next_state = _TRANSITIONS[(self.state, event)]
            except KeyError as exc:
                raise InvalidTransition(self.state, event) from exc

        state_latency = now_ms() - self._entered_ms
        prev = self.state
        self.state = next_state
        self._entered_ms = now_ms()

        if self.logger is not None:
            self.logger.log(
                session_id=self.session_id,
                state=next_state.value,
                event=event.value,
                state_latency_ms=round(state_latency, 2),
                error_type=error_type,
                **{k: v for k, v in log_fields.items()},  # type: ignore[arg-type]
            )
        return next_state

    def reset(self) -> State:
        """Force the machine back to IDLE (used after ERROR or shutdown)."""
        return self.fire(Event.RESET) if self.can(Event.RESET) else self._force_idle()

    def _force_idle(self) -> State:
        prev = self.state
        self.state = State.IDLE
        self._entered_ms = now_ms()
        if self.logger is not None:
            self.logger.log(
                session_id=self.session_id,
                state=State.IDLE.value,
                event=Event.RESET.value,
                extra={"forced_from": prev.value},
            )
        return self.state
