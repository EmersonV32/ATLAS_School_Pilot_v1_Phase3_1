# Current state

Status date: 2026-08-29

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

Reconciliation and device validation on 2026-08-29 produced:

- `276 passed` from the complete suite during the successful Jetson deployment;
- `277 passed` locally after adding the disconnected-camera regression;
- passing obvious-secret and recovery-bundle checks;
- a successful XIAO ESP32-S3 Sense firmware compile for the balanced
  800x600/15 FPS profile;
- HTTP 200 responses for visitor, staff, health, and bootstrap endpoints from
  another computer while the camera was unplugged;
- successful camera hot-plug recovery without restarting the website service,
  followed by automatic recovery from one induced MJPEG read failure;
- a healthy `atlas.service` after the camera-independent deployment; and
- one non-failing Starlette deprecation warning from the installed FastAPI
  test client.

The active work is on `codex/jetson-runtime-reconcile`. It has not been merged
into GitHub `main`. The exact device state and rollback information are in
[`jetson/JETSON_RUNTIME_STATUS.md`](jetson/JETSON_RUNTIME_STATUS.md).

## Physical validation still required

The following cannot be proven from a laptop-only session:

- XIAO firmware flashing and a 20-minute sustained thermal/FPS test;
- sustained camera streaming, 800x600 firmware flashing, thermal behavior, and
  live artwork detection with the new profile;
- Traditional Chinese live STT and TTS provider behavior;
- a physical Shokz multifunction-button manual capture;
- headset disconnect/reconnect recovery after boot; and
- Cartesia recovery after its HTTP 402 account/billing failure is resolved.

Use the Jetson section of [`VALIDATION_CHECKLIST.md`](VALIDATION_CHECKLIST.md)
before declaring a deployment complete.
