# Jetson Runtime Status

Updated: 2026-08-29

## Source and recovery authority

- Integration branch: `codex/jetson-runtime-reconcile`.
- Latest deployed source commit: `6ec6197`.
- Live runtime: `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`.
- Recovery clone: `/home/super-alex/atlas/ATLAS_School_Pilot_v1_Phase3_1`.
- Python environment: `/home/super-alex/atlas/venvs/atlas-school-pilot`.
- User service: `atlas.service`.
- Service command: `python -m atlas.app.main --mode device --device-loop`.
- Visitor dashboard: `http://10.0.0.238:8765/` on the current LAN.
- Staff dashboard: `http://10.0.0.238:8765/admin` on the current LAN.
- Device settings and secrets remain local in ignored files. They are preserved
  by the deployment script and are not Git recovery artifacts.

The reconciliation branch is pushed to GitHub but is not merged into `main`.
Do not describe GitHub `main` as the physical Jetson authority until the branch
has passed review and been merged.

## Verified on 2026-08-29

- The latest Chinese-support deployment passed `280` Jetson tests. The local
  suite also passed `280` tests, with the single existing Starlette deprecation
  warning.
- `atlas.service` starts and remains healthy while the camera is unplugged.
- Visitor, staff, health, and bootstrap endpoints return HTTP 200 from another
  computer on the LAN while the camera is unplugged.
- After the camera was reconnected, the visitor API changed to `Camera health
  signal is fresh` without a website or service restart. A captured frame from
  the currently flashed firmware measured 640x480.
- A competing direct capture briefly stalled the MJPEG reader. ATLAS reported
  the failure, reconnected automatically, and returned to fresh frames with
  `reconnect_count: 1` and zero consecutive failures.
- Traditional Chinese is a validated visitor language: the onboarding locale,
  admin controls, Gemini response prompt, manual-capture phrases, timeout
  fallback, and Piper fallback are all wired to `zh` / `zh-Hant`. A live typed
  question returned a Chinese answer while the visitor session remained idle.
  Arabic remains a preview language.
- Shokz input/output readiness is healthy. The multifunction button is exposed
  as `/dev/input/event2`, key code `164`, and is configured for manual capture.
- Gemini and Deepgram are ready. Local Whisper is available as speech-to-text
  fallback. Cartesia is unavailable after the latest restart, so Piper is the
  verified text-to-speech fallback. The verified Chinese Piper model is
  `/home/super-alex/piper_voices/zh_CN-huayan-medium.onnx`.
- The balanced XIAO camera firmware profile compiles for
  `esp32:esp32:XIAO_ESP32S3` with OPI PSRAM and the 8 MB application partition.
  The compiled sketch uses 1,031,466 bytes of flash and 70,616 bytes of global
  memory.
- The balanced firmware was flashed successfully through Windows `COM3` and
  verified by ATLAS with an 800x600 JPEG. A six-sample post-flash check kept
  fresh frames at approximately 12.4 to 14.8 FPS with no reconnects or failures.

## Rollback point

The pre-deployment snapshot is retained on the Jetson at:

`/home/super-alex/atlas/snapshots/atlas_live_pre_8eae94f_20260829.tar.gz`

- Size: approximately 40 MB.
- SHA-256:
  `3033739fce0fa1ab39ee514cd4b3d1d035819bc5afb34b2df0d6030917e7e19e`.
- The same snapshot directory contains the service definition and Python
  package freeze used for recovery.
- The successful atomic deployment also retained
  `/tmp/atlas_visitor_backup_20260829_175759`.

## Current hardware and flow status

| Component or flow | Status | Notes |
| --- | --- | --- |
| Jetson Orin NX / J401 | Working | Device runtime and user service are healthy. |
| Visitor and staff dashboards | Working without camera | Both remain reachable and report camera disconnection instead of blocking startup. |
| Shokz microphone and speaker | Ready | Runtime readiness reports both audio directions available. |
| Shokz multifunction button | Ready | Manual capture is mapped to input event key `164`; physical press should be rechecked before a demo. |
| XIAO ESP32-S3 Sense camera | Connected on new firmware | ATLAS receives fresh 800x600 frames at a 15 FPS target. Hot-plug and automatic stream recovery work; sustained thermal validation remains required. |
| Camera firmware profile | Flashed and short-tested | SVGA 800x600 JPEG, quality 10, maximum 15 streamed FPS, idle Wi-Fi power saving. |
| Gemini | Ready | Cloud response provider is available. |
| Deepgram / Whisper | Ready with fallback | Deepgram is primary; local Whisper is fallback. |
| Cartesia / Piper | Degraded with fallback | Cartesia is unavailable at the latest service check; Piper is ready for English, French, and Traditional Chinese. |
| Traditional Chinese | Runtime verified | `zh-Hant` onboarding maps to `zh`; a live typed answer was Chinese and the local Piper model synthesized a valid WAV. |
| YOLO artwork detection | Runtime present, hardware test pending | Cannot verify visual detection while the camera is unplugged. |
| EV3 / mechanical outputs | Disabled | `enable_ev3: false`; no current physical verification. |

## Deployment and rollback procedure

Use `atlas/scripts/deploy/DEPLOY_ATLAS_VISITOR_IMPROVEMENTS.ps1` from the
repository checkout. It packages the tracked runtime, tests, content, and
firmware; preserves device settings and dashboard overrides; stops the service;
replaces source trees atomically; runs the complete test suite against the
repository development configuration; restores device-local configuration;
starts the service; and checks health. A failed test or health check restores
the prior runtime trees.

Never replace the ignored Jetson `.env`, XIAO `wifi_secrets.h`, device
`settings.yaml`, dashboard overrides, databases, or model caches with files
from GitHub.

## Required next physical checks

1. Stream continuously for 20 minutes while recording FPS and enclosure
   temperature; stop if temperature rises abnormally or frames become unstable.
2. Confirm the flashed stream remains fresh with ATLAS as its only MJPEG client.
3. Trigger manual capture using the Shokz multifunction button and verify that
   the selected artwork context updates.
4. Run one live artwork identification and spoken Chinese question through the
   complete Deepgram, Gemini, and Piper fallback path on the Shokz headset.

## Known risks

- The XIAO firmware has passed physical flash and short-run streaming checks,
  but not the required 20-minute thermal test. Do not seal it into the wearable
  enclosure yet.
- The current camera server can be disrupted by a competing capture client.
  Route previews through ATLAS's `/camera/frame.jpg` endpoint instead of opening
  a second direct connection to the XIAO stream.
- Cartesia speech is unavailable at the latest service check. Verify the new
  Scale-plan credential/billing state before relying on it; Piper is the
  current operational fallback.
- The dashboard URLs use the Jetson's current LAN address. A public Vercel site
  would require a separate hosted frontend and a secure relay/API to the Jetson;
  replacing the LAN URL alone would not expose the local runtime safely.
- GitHub recovery excludes secrets, Wi-Fi credentials, generated indexes,
  downloaded models, runtime logs, and captured visitor media. Restore those
  from the private recovery inventory after cloning.
