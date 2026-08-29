# Current state

Status date: 2026-08-28

## Active implementation

The current runtime is `../atlas/`. It includes the integrated Python package,
visitor and staff dashboards, content sources, tests, firmware, configuration,
and Jetson deployment/recovery scripts.

Implemented behavior includes:

- automatic and manual artwork capture;
- museum retrieval combined with general Gemini responses when retrieval is
  not relevant;
- bounded conversational context for artwork and artist follow-ups;
- speech recognition and synthesis provider integrations;
- response-level TTS provider locking;
- visitor profiles, accessibility choices, and multilingual interface assets;
- multifunction-headset manual capture handling;
- readiness refresh and continuous experience controls;
- versioned artwork source manifests and a recovery-bundle verifier.

## Verification state

Laptop validation on 2026-08-28 after the structural reorganization produced:

- `257 passed` from the complete pytest suite;
- a passing obvious-secret scan and recovery-bundle verifier;
- successful Python compilation and dependency consistency checks;
- a passing Ruff check for the changed recovery verifier;
- one non-failing Starlette deprecation warning from the installed FastAPI
  test client.

The repository-wide Ruff scan still reports pre-existing style findings in
runtime and test files that were moved without behavioral edits. They are not
part of this structural change and remain cleanup work.

The reorganized baseline commit
`ac06623e476633f0aef14c9c49e8606da40857c4` was pushed to `main`, cloned into a
new temporary directory, and passed the recovery-bundle verifier. The fresh
clone contained only `.github`, `.gitignore`, `AGENTS.md`, `README.md`,
`archive/`, `atlas/`, and `handoff/` at repository root.

## Physical validation still required

The following cannot be proven from a laptop-only session:

- Jetson camera discovery and sustained capture;
- CUDA, TensorRT, PyTorch, and model compatibility;
- Deepgram and Cartesia behavior with production keys and museum networking;
- Traditional Chinese live STT and TTS provider behavior;
- Shokz multifunction-button events and manual capture;
- headset disconnect/reconnect recovery after boot;
- single-voice playback across real streaming responses;
- systemd startup, restart, and dashboard reachability on the museum network.

Use the Jetson section of [`VALIDATION_CHECKLIST.md`](VALIDATION_CHECKLIST.md)
before declaring a deployment complete.
