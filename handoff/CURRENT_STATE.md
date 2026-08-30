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

- `280 passed` from the complete suite during the latest successful Jetson
  deployment;
- `280 passed` locally after the same Chinese-support changes;
- passing obvious-secret and recovery-bundle checks;
- a successful XIAO ESP32-S3 Sense firmware compile for the balanced
  800x600/15 FPS profile;
- a successful physical flash of that profile, with a fresh 800x600 frame and
  six short-run samples at approximately 12.4 to 14.8 FPS;
- HTTP 200 responses for visitor, staff, health, and bootstrap endpoints from
  another computer while the camera was unplugged;
- successful camera hot-plug recovery without restarting the website service,
  followed by automatic recovery from one induced MJPEG read failure;
- a healthy `atlas.service` after the camera-independent deployment; and
- one non-failing Starlette deprecation warning from the installed FastAPI
  test client.

Traditional Chinese is now a validated visitor/runtime path: `zh-Hant`
onboarding maps to `zh`, the live Gemini path returned a Chinese museum answer,
and the configured Jetson Piper model synthesized a valid Chinese WAV. Cartesia
remains unavailable, so Piper is the active speech fallback.

The active work is on `codex/jetson-runtime-reconcile`. It has not been merged
into GitHub `main`. The exact device state and rollback information are in
[`jetson/JETSON_RUNTIME_STATUS.md`](jetson/JETSON_RUNTIME_STATUS.md).

## Physical validation still required

The following cannot be proven from a laptop-only session:

- XIAO firmware flashing and a 20-minute sustained thermal/FPS test;
- sustained camera streaming, thermal behavior, and live artwork detection
  with the flashed 800x600 profile;
- physical Chinese STT and headset playback through the complete live flow;
- a physical Shokz multifunction-button manual capture;
- headset disconnect/reconnect recovery after boot; and
- Cartesia recovery after its HTTP 402 account/billing failure is resolved.

Use the Jetson section of [`VALIDATION_CHECKLIST.md`](VALIDATION_CHECKLIST.md)
before declaring a deployment complete.
