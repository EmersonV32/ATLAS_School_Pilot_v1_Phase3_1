# Current state

School Wi-Fi preparation, 2026-10-05 (local source only): optional camera
PEAP/MSCHAPv2 support and an operator-run credential helper are prepared for
`CBourget` under the user's explicitly unverified authentication assumption.
The camera selects visible school Wi-Fi before the unchanged hotspot, with a
30-second school authentication window. The Jetson helper stages an inactive
profile with priority 100 and one automatic activation attempt; the documented
local-console step enables it and sets the existing hotspot to priority 50.
Neither device preempts a working hotspot. Both authenticate independently and
can end up on different networks; fallback does not establish peer reachability.
No real credentials were read/written, no camera flashed, and no Jetson profile
installed/enabled during this preparation. All three synthetic firmware variants
compile on core 3.3.11; final helper gate 30 passed and full suite 3,033 passed /
1 skipped. Changed Python lint, secret/recovery, dependency and diff checks pass;
broader runtime/test lint retains 31 existing findings in untouched files.
Physical authentication/fallback remain untested. The
separately diagnosed camera stream-watchdog race remains unpatched. See
[`../atlas/docs/SCHOOL_WIFI_SETUP.md`](../atlas/docs/SCHOOL_WIFI_SETUP.md).

Jetson deployment update, 2026-10-04 at 18:38 EDT: at the user's explicit request,
v6 and the five runtime fixes are now deployed. The service is active in device
mode with a newly built/verified FP16 engine at 416, healthy retrieval/speech
readiness, and fresh camera/headset readiness signals. Native suite: 3,002 passed,
2 expected skips. Original device config/unit hashes are unchanged, and a durable
pre-v6 rollback backup is preserved. See
[`../atlas/docs/2026-10-04_JETSON_V6_DEPLOYMENT.md`](../atlas/docs/2026-10-04_JETSON_V6_DEPLOYMENT.md)
for exact artifacts, the corrected Linux test-harness failure/confirmed rollback,
and remaining live-camera/voice/thermal acceptance checks. No Git commit/push or
NVIDIA/package/firmware changes occurred.

The local-only integration description below records the earlier stage.

Local integration update, 2026-10-04: at the user's explicit request, v6 now
occupies `../atlas/models/atlas_yolo.pt`, with its matching recovery manifest.
The exact previous model is preserved in `models/releases/2026-09-07-camera-domain-rollback/`.
Real CPU loader/detector/tracker checks passed at 416 with the recorded Jetson
library versions (Ultralytics 8.4.115, PyTorch 2.8.0 CPU); this is **not** a
Jetson/XIAO/TensorRT test. Engine selection now requires matching checkpoint,
engine and input-size provenance. Five runtime fixes are also present locally.
No commit, push or physical deployment was performed. See
[`../atlas/docs/2026-10-04_V6_LOCAL_INTEGRATION.md`](../atlas/docs/2026-10-04_V6_LOCAL_INTEGRATION.md)
and [`2026-10-04_NEW_CHAT.md`](2026-10-04_NEW_CHAT.md). The device observations
below remain dated, not an October physical-health check.

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
