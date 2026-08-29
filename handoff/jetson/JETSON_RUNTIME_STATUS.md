# Jetson Runtime Status

Updated: 2026-08-09

## Source and startup

- Sync branch: `codex/jetson-runtime-sync`.
- Local base commit before this runtime-sync commit: `5ec608f4c43159a69af78e49c44f8e07f0e66056`.
- Jetson runtime directory: `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`.
- Python environment: `/home/super-alex/atlas/venvs/atlas-school-pilot`.
- Normal service: `systemctl --user start atlas.service`.
- Service command: `python -m atlas.app.main --mode device --device-loop`.
- Dashboard: `http://127.0.0.1:8765/admin` on the Jetson. It is loopback-only.
- Runtime configuration: `config/settings.yaml` plus an ignored local `.env` for API keys.

The live Jetson was updated through a reviewed deployment archive, not by a
confirmed Git checkout. Its exact Git revision therefore remains unverified.

## Verified on the physical Jetson

- Jetson Orin NX runtime starts, becomes healthy, and serves the admin
  dashboard after deployment.
- Shokz OpenComm2 UC playback and microphone work with ATLAS.
- Deepgram Nova-3 plus Silero VAD produces live English transcripts.
- Gemini 2.5 Flash streams answers.
- Cartesia Sonic 3.5 speaks streamed answers through one continuous context.
  The 2026-08-09 runtime log recorded the same Cartesia voice ID throughout
  multi-sentence responses, with no Piper fallback voice takeover.
- The RAG demo pack is indexed with 7 artworks and 157 chunks in both the
  vector store and SQLite FTS5.
- The XIAO ESP32-S3 Sense MJPEG camera stream opens and reconnects after a
  stream failure. The dashboard receives frames from the in-memory reader.

## Current hardware and flow status

| Component or flow | Status | Notes |
| --- | --- | --- |
| Jetson Orin NX / J401 | Working | Device runtime and user service run. |
| Shokz microphone and speaker | Working | Real Deepgram input and Cartesia output verified. |
| XIAO ESP32-S3 Sense camera | Partially verified | It streams, but `atlas-camera.local` has intermittent name resolution and the MJPEG stream can stall. The runtime now recovers automatically. |
| Router / network | Partially verified | Internet is sufficient for cloud calls, but local mDNS is not fully reliable. |
| YOLO artwork detection | Not re-verified in the latest live session | Latest captured questions used all-artwork RAG because no active camera context was latched. |
| EV3 / mechanical outputs | Disabled | `enable_ev3: false`; no current physical verification on this Jetson. |
| Status LED / RGB strip | Not verified | No current enabled hardware adapter. |
| Shokz multi-function button | Code present, not physically verified | One click cycles language, two clicks capture artwork, three clicks resets context. |
| Visitor dashboard | Mock-backed on GitHub main | It is not yet connected to real runtime state. |

## Known failures and workarounds

- Camera mDNS: when `atlas-camera.local` does not resolve, ATLAS continues
  listening without visual context and retries the camera. Reserve a static
  IP address for the XIAO on the router, then replace the camera URL in the
  local device configuration to eliminate this dependency.
- Camera stream stalls: the runtime clears stale frames and reconnects. The
  new network-read timeout is deployed but still needs a focused live camera
  stress test.
- Deepgram can temporarily fail during a DNS outage. ATLAS then uses local
  Whisper, which is much slower; later Deepgram calls may recover.
- Only `demo_pack` is verified as the active physical RAG pack. The admin UI
  can list and re-index packs, but selecting another pack does not yet
  reconfigure the running device retriever. Treat multiple live packs as
  unsupported until that behavior is implemented and tested.
- The full end-to-end audit has not been run because it requires explicit
  approval before starting.

## Sensitive and generated files excluded from Git

- `.env`, API keys, tokens, SSH private keys, and XIAO Wi-Fi credentials.
- Runtime logs, transcript data, raw audio/images, SQLite/Chroma databases,
  model caches, ONNX/TensorRT exports, and build artifacts.

## Safe reconciliation and update path

1. Preserve this branch and compare it against GitHub `main`.
2. Reconcile source changes in a new integration branch; do not force-push or
   merge directly into `main` from the Jetson.
3. On the Jetson, back up the current runtime and local `.env`, fetch the
   reconciled branch, and review `git diff` before applying it.
4. Run the focused test suite and RAG ingestion, then restart
   `atlas.service` and confirm `/health` before a live hardware check.
5. Retain the prior runtime directory or deployment archive until the camera,
   microphone, TTS, and dashboard checks pass.
