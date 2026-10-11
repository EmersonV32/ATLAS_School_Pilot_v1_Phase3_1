# Jetson v6 deployment — October 4, 2026

The user explicitly approved Jetson deployment after local integration.
V6 and the five runtime fixes are now deployed to
`/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated` on `super` (`10.0.0.238`).
The source is the working tree of `codex/v6-model-handoff-2026-10-04`;
no Git commit, push or main merge was performed. NVIDIA/L4T packages, holds,
Python packages, power modes, firmware flashing and EV3 calibration were not
changed. Existing device configuration and service-unit contents were preserved.

## Deployed artifacts

- Portable checkpoint SHA-256:
  `af11b2de376a5c54a1ee11e9765f91ecbf54a1f308a2a82f9106b00a78409731`.
- New target-built TensorRT FP16 engine SHA-256:
  `6cb18c4a51a80300910808cfba0a9aba4c925a75dd1fa76109b5e04c14d25c17`.
- Input size: 416; seven numeric classes match ATLAS's content labels.
- Python 3.10.12, Ultralytics 8.4.115, PyTorch 2.8.0, CUDA available,
  TensorRT 10.3.0 on the Orin GPU. No dependency upgrades were needed.
- Engine export occurred on this Jetson in an isolated staging directory and
  took 555.2 seconds. Automatic package installation/network model lookup were
  disabled. The engine binding sidecar matches checkpoint, engine and input size.

## Validation and cutover

- The exact extracted deployment bundle passed the laptop runtime gate.
  Packaging was corrected to include the training-tool fixtures, portable
  release/rollback weights and approved public artwork references needed by tests.
- Final local suite: **3,003 passed, 1 skipped**. Final Jetson staging and live
  installation suites: **3,002 passed, 2 skipped**. The skips are opt-in CPU ML
  testing and the full-checkout/Windows-only uploader test. One existing
  Starlette/httpx deprecation warning remains.
- Deployment tests avoid reading the live installation's `.env` while preserving
  synthetic test fixtures. All 26 rollback scenarios cover direct export and
  staged-engine promotion. Changed-file Ruff, secret scan, recovery verifier and
  diff checks passed.
- The first live validation stopped on a Linux-only fault-injection harness
  bug: matching the entire argument string mistook `pytest-of-*` staging paths
  for the pytest command. Automatic rollback restored the original PT, engine,
  configuration and service unit; all four hashes and healthy service were
  independently confirmed. Dispatch now uses the script argument. Native and
  laptop full gates passed before the successful retry.
- Cutover used only the engine just built on this exact Jetson, verifying
  provenance, copied checksums, GPU warm-up and class order. The default workflow
  still builds directly on the target when no staged root is supplied.

## Public-reference PT/TensorRT inference

Real GPU checks used public Mona Lisa/Great Wave source assets and a black blank
frame, without opening any additional camera, microphone or cloud session.
Both backends returned the expected IDs; the blank had no detection.

At matched square 416 inputs, box IoU was 0.999493 for Mona Lisa and 0.998911
for Great Wave, with confidence differences below 0.001. Original-aspect
references also matched IDs, with box IoU 0.988002 and 0.957861 respectively.
The backend-dependent rectangular preprocessing explains why those original
aspect cases are not identical to the matched-square numerical comparison.

In a short staged 20-iteration public-square check, median detector-call wall
times were 45.23 ms for PT and 20.40 ms for TensorRT. These are **not** fresh-camera
accuracy, camera-to-speech latency or a sustained thermal-soak benchmark.
A brief build-time telemetry sample showed GPU about 49 C and CPU about 52 C;
no thermal-soak acceptance claim is made.

## Running service and dashboards

`atlas.service` entered active/running state at **18:38:48 EDT** with
`NRestarts=0`, `ExecMainStatus=0`. The running process has TensorRT loaded.
Both loopback and LAN `/health` report `status=ok`, `mode=device`,
`vision=YoloDetector`, healthy retrieval and ready STT/TTS providers.
Visitor and admin pages return HTTP 200; unauthenticated `/status` returns 401.
Camera and headset readiness signals are good. The readiness endpoint's only
blocker is the expected instruction to choose a visitor language.

- Visitor: <http://10.0.0.238:8765/>
- Admin: <http://10.0.0.238:8765/admin>

Configuration SHA-256 remains
`b4824f898fd834bd769fd94dae8be76425e6781a72f5f7be47cd0b284cfc3278`;
the installed service-unit SHA-256 remains
`3baed50739465245c99eba94b7840b87e7f4057b15a4c62cfc7ebb66145eb326`.
EV3/servo remain disabled as before. No visitor logs, existing runtime databases,
secrets, keys or raw camera media were inspected.

## Durable rollback backup

The successful transaction's complete pre-v6 backup was copied and verified at:

`/home/super-alex/atlas/backups/atlas_visitor_backup_20261004_183653_7cfa3bd5`

It contains the old runtime/content, PT, engine, model manifest, device config
and installed service unit. It is outside `/tmp`, so a normal reboot will not
erase it. The temporary transaction backup remains too.

Old PT SHA-256:
`5680d3a5fff21d482e579c47f0b19e030b6acbdefdfe5da188de9cc961a66bec`.
Old engine SHA-256:
`0c418387cc2a9a95f8fdcb5b6fa5b77b1b59c94d2821416ec392bc28af7a7e3c`.

## Still unverified

Fresh session-separated XIAO footage covering all seven artworks and unrelated
scenes, miss/false-alarm acceptance, an actual spoken end-to-end headset rehearsal,
sustained thermals and physical iPad/reduced-motion checks remain due. Public
reference smoke tests and ready provider signals do not establish those results.
This is a deployed prototype, not a completed school-pilot acceptance test.
