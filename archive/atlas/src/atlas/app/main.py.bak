"""ATLAS application entrypoint.

Phase 1 scope: load configuration, build the container and logger, create a
state machine, and run a short scripted transition sequence so that
`python -m atlas.app.main --mode dev` runs end-to-end without any hardware
or ML dependencies. The full orchestration loop (vision -> STT -> RAG ->
LLM -> validate -> TTS) is wired in later phases.

ATLAS uses an edge-first architecture: vision, speech, retrieval, motor
control, and text-to-speech run locally or nearby, while the current
prototype uses a cloud language model for final response generation. A
future version aims to replace this with an on-device language model.
"""

from __future__ import annotations

import argparse

from atlas.app.dependency_container import build_container
from atlas.app.events import Event
from atlas.app.state_machine import StateMachine
from atlas.models.enums import RunMode
from atlas.utils.ids import new_session_id


def _scripted_dev_walkthrough(sm: StateMachine) -> None:
    """Fire one happy-path question cycle through the state machine.

    Demonstrates that transitions and logging work. No real I/O.
    """
    sequence = [
        Event.START_LISTENING,
        Event.AUDIO_CAPTURED,
        Event.TRANSCRIBED,
        Event.ARTWORK_DETECTED,
        Event.RETRIEVED,
        Event.GENERATED,
        Event.VALIDATION_PASSED,
        Event.SPOKEN,
        Event.FOLLOWUP_TIMEOUT,
    ]
    for event in sequence:
        state = sm.fire(event)
        print(f"  {event.value:<28} -> {state.value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ATLAS School Pilot v1")
    parser.add_argument(
        "--mode",
        choices=[m.value for m in RunMode],
        default=None,
        help="Run mode (overrides config). dev|local|device|demo",
    )
    parser.add_argument(
        "--config-dir", default="config", help="Path to the config directory"
    )
    args = parser.parse_args()

    container = build_container(args.config_dir)
    if args.mode:
        container.settings.mode = RunMode(args.mode)

    settings = container.settings
    print("ATLAS School Pilot v1")
    print(f"  mode          : {settings.mode.value}")
    print(f"  default pack  : {settings.default_pack_id}")
    print(f"  llm provider  : {settings.llm.provider}")
    print(f"  logs dir      : {settings.paths.logs_dir}")
    print(f"  log transcripts: {settings.logging.log_transcripts}")

    session_id = new_session_id()
    sm = StateMachine(session_id=session_id, logger=container.logger)
    print(f"\nSession {session_id} - scripted dev walkthrough:")
    _scripted_dev_walkthrough(sm)
    print("\nDone. Transitions logged to", settings.paths.logs_dir)


if __name__ == "__main__":
    main()
