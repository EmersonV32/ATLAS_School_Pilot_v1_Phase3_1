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
import logging

from atlas.app.dependency_container import build_container
from atlas.app.events import Event
from atlas.app.state_machine import StateMachine
from atlas.models.enums import RunMode
from atlas.utils.ids import new_session_id


def _configure_runtime_logging(level: str) -> None:
    """Emit all ATLAS module logs to the process stream captured by systemd."""
    atlas_logger = logging.getLogger("atlas")
    atlas_logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    if not any(
        getattr(handler, "_atlas_runtime", False)
        for handler in atlas_logger.handlers
    ):
        handler = logging.StreamHandler()
        handler._atlas_runtime = True  # type: ignore[attr-defined]
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        atlas_logger.addHandler(handler)
    atlas_logger.propagate = False


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
    parser.add_argument(
        "--run",
        type=int,
        default=0,
        metavar="N",
        help="Run N complete pipeline interactions",
    )
    parser.add_argument(
        "--device-loop",
        action="store_true",
        help="Run the real camera-driven device loop until Ctrl+C",
    )
    parser.add_argument(
        "--wait-ready",
        action="store_true",
        help="Preload every component, then wait for Enter before interaction",
    )
    args = parser.parse_args()

    container = build_container(args.config_dir)
    if args.mode:
        container.settings.mode = RunMode(args.mode)

    settings = container.settings
    _configure_runtime_logging(settings.logging.level)
    print("ATLAS School Pilot v1")
    print(f"  mode          : {settings.mode.value}")
    print(f"  default pack  : {settings.default_pack_id}")
    print(f"  llm provider  : {settings.llm.provider}")
    print(f"  logs dir      : {settings.paths.logs_dir}")
    print(f"  log transcripts: {settings.logging.log_transcripts}")
    print(f"  log live STT   : {settings.logging.log_live_stt}")
    print(f"  log LLM answers: {settings.logging.log_llm_responses}")

    if settings.mode == RunMode.DEVICE and (args.run > 0 or args.device_loop):
        from atlas.app.device_runtime import DeviceRuntime

        runtime = DeviceRuntime(container)
        try:
            runtime.run(
                max_interactions=args.run,
                wait_for_terminal=args.wait_ready,
            )
        except KeyboardInterrupt:
            print("\nATLAS stopped safely.")
        except RuntimeError as exc:
            print(f"\nATLAS could not start: {exc}")
            raise SystemExit(2) from exc
        return

    if args.run > 0:
        runner = container.session_runner
        print(f"\nRunning {args.run} pipeline cycle(s):")
        for i in range(1, args.run + 1):
            print(f"\n--- Cycle {i} ---")
            result = runner.run_once(frame=None)
            if result.success:
                print(f"  Artwork : {result.detection.label}")
                print(f"  Q       : {result.transcript.text}")
                print(f"  A       : {result.dialogue.response[:90]}")
            else:
                print(f"  (no cycle: {result.error})")
        print("\nDone. Logged to", settings.paths.logs_dir)
        return

    session_id = new_session_id()
    sm = StateMachine(session_id=session_id, logger=container.logger)
    print(f"\nSession {session_id} - scripted dev walkthrough:")
    _scripted_dev_walkthrough(sm)
    print("\nDone. Transitions logged to", settings.paths.logs_dir)


if __name__ == "__main__":
    main()
