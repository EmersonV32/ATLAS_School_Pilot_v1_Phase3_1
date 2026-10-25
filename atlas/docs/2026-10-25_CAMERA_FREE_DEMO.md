# October 25: camera-free demo deployment and remaining hardware work

## Current outcome

The owner's Jetson and OpenComm are online. The XIAO camera is physically
offline: the owner reports a damaged BAT+ contact. This source update makes
camera absence non-blocking for spoken conversations, without pretending that
vision, capture or preview is available.

The owner initially reported that the demo would not start, then corrected the
report: **the demo works**. The owner also reports a voice break/change, first
in French and then clarified to affect all languages. That problem remains
OPEN. At the last exchange the owner was restarting ATLAS to retest. A restart
temporarily clearing the symptom is not root-cause resolution.

## Exact release and preservation

- Work branch: `codex/camera-offline-demo-2026-10-25`; main is unchanged.
- Installed implementation: `d9b062b3868cd4c4a5122a1cf29d3bc5f0f609ab`.
- Public source-only archive: `ATLAS-camera-offline-source.zip`, SHA-256
  `0fd3e365559a27d94d70bbc0531a245106c1e999494af81688166a9d69193984`.
- Target staging folder: `/home/super-alex/atlas/onsite-20261025`.
- Existing install: `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`.
- Existing Python: `/home/super-alex/atlas/venvs/atlas-school-pilot/bin/python`.
- Existing user `atlas.service` was restarted once by the source transaction.
- Source rollback backup:
  `/home/super-alex/atlas/backups/onsite-20261025/atlas-source-20261025-140856-fbeddd54`.

Native isolated preflight/apply validation passed. All **188 installed managed
files** match the approved manifest. Post-update service was active/running,
`NRestarts=0`, `ExecMainStatus=0`; actual versioned assets return 200 and
protected unauthenticated routes still return 401. Health identifies Gemini,
Deepgram, Cartesia, local fallbacks, YOLO and both retrieval stores as ready.
The `MockHardware` component is the unconnected EV3/motion adapter, not mock AI.

No model/engine, service unit, packages, boot settings, firmware, Wi-Fi,
provider/voice settings, audio routing, museum content or private configuration
was changed. No credentials, visitor logs, private dialogue or raw media was
read. Follow-up documentation/browser QA commits are not runtime modifications
and are not included in this exact installed archive.

## What changed

- Disconnected or stale artwork camera is `degraded`, not a start blocker.
  Unit, headset, language, AI/content and emergency-stop checks remain enforced.
- Both staff demo and visitor onboarding can start without vision.
- Dashboard explicitly says voice is available; capture is disabled without
  a fresh frame and automatically re-enables when fresh frames return.
- The existing runtime continues listening without frames. Questions naming
  an artwork and staff manual Artwork context selection remain available;
  real camera recognition/physical capture cannot identify an unseen artwork.
- Admin JavaScript is versioned `v23` to avoid retaining the old start UI.

Operator: refresh the actual Jetson dashboard (`http://10.0.0.238:8765/admin`
was reachable today), choose a language and Start demo. DHCP addresses can
change. Ask about an artwork by name, then a pronoun follow-up. Staff may use
the existing Artwork context override instead of a camera. Start demo does not
require the visitor wake phrase; visitor onboarding still does.

## Verification

- Full isolated synthetic Python suite: **3,480 passed, two skipped**.
  Non-failing warnings: existing TestClient deprecation and intentional
  duplicate-ZIP negative fixture.
- Focused readiness/API/runtime regressions: **140 passed**. They cover camera
  absence/staleness/recovery, manual artwork context, camera-free demo voice
  dispatch, auth and continued rejection of genuine blockers.
- Synthetic admin JavaScript: **106 checks**.
- Actual HTML/CSS/JS in headless Chrome with synthetic APIs: **35 layouts,
  32 actions, 11 failure/recovery cases, 2,727 contrast checks, zero unexpected
  browser errors**. Includes offline-camera demo start/stop and capture recovery.
- Visitor flow: **42 keyboard transitions**, 1024x768 landscape, reduced
  motion, successful camera-degraded start, no cookies/local/session storage
  or IndexedDB, zero browser errors.
- Ruff, dependency, secret, recovery and whitespace checks pass.

These tests do not establish sustained cloud voice quality or physical servo
safety. Follow-up native health metadata after the reported voice issue showed
last STT Deepgram and last TTS Cartesia; this does not prove why the voice varied.
The one-whole-answer/fixed-voice and no-mid-answer-fallback protections are
already installed. Do not re-enable sentence-at-a-time TTS as an activation fix.

## Dashboard activation boundaries

Existing completed software features are installed, not merely staged: demo,
conversation/RAG/context, staff controls, redesigned dashboard, synchronized
readable activity and technical view, and the optional pan controller/API.
Controls still reflect actual prerequisites. An inactive camera preview is not
an unfinished speech feature; CSI preview is opened lazily from its own tab.

Do not fabricate healthy camera/audio/pan status or enable disconnected EV3,
unimplemented human tracking, unverified language speech paths, raw transcript
logging or motor motion to eliminate inactive labels. Those are hardware,
future-feature or privacy boundaries, not deployment omissions.

## Next acceptance steps / unresolved issues

1. **All-language voice change: OPEN, demo risk.** After the owner's restart,
   try a short and a long answer in English and French; distinguish a cutoff
   from a changed speaker/accent. Record non-sensitive outcome/provider
   metadata, not private dialogue. Do not claim a fix from a temporary recovery.
2. **Camera: physical repair needed.** Repair safely with power disconnected;
   software cannot repair a lifted battery contact. After repair, test camera
   reconnect, fresh-frame capture, automatic artwork selection and sustained
   conversation while the camera disappears/returns.
3. **Camera-free context:** live same-artwork, A-to-B-to-A and staff override
   checks with the current release remain due beyond the owner's demo-start
   confirmation. October 18 context acceptance remains dated evidence.
4. **School Wi-Fi:** saved provisioning was not changed. Actual school AP
   authentication, 2.4 GHz camera access, client isolation, fallback and provider
   access still need testing at school; home success cannot certify them.
5. **SG90:** controller/dashboard installed; hardware output OFF. Read-only PWM
   discovery passed for pin 32 and pin 15 controllers, but power supply,
   pinmux/waveform, signal compatibility, travel and mount are unverified.
   The owner has only identified the servo/three-socket plug so far. Follow
   [the wiring and commissioning guide](CAMERA_PAN.md); do not connect that
   three-socket block across adjacent header pins or enable full sweep first.
6. **Combined physical acceptance:** CSI preview, verified bare-servo movement,
   manual override/release, safety stop, power stability under camera/audio load,
   cable clearance and cold boot must be supervised after commissioning.

No further live changes were made while the owner restarted the service.
