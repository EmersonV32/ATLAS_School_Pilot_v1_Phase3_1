# School director demo: teammate/Codex handoff

**Historical October 18 record.** For the current takeover use the
[October 26 handoff](2026-10-26_TEAMMATE_HANDOFF.md) and
[deployment runbook](DEPLOYMENT_RUNBOOK.md). Older branch, installed revision,
network assumptions, and test counts below describe their original date.

Status: October 18, 2026 evening (America/Toronto). Read this and
[CURRENT_STATE.md](CURRENT_STATE.md) first. Work only from `atlas/`, following
both repository and application `AGENTS.md`. This is an honest acceptance
record, NOT a claim that every hardware/cloud scenario passed.

## Checkout and installed release

- Pull/check out **`codex/onsite-deployment-ready`**. `main` was not promoted.
  This branch includes the combined voice/context/listening/dashboard/activity
  work and disabled direct SG90 implementation. Do not deploy archive copies.
  The branch and this handoff were successfully pushed to GitHub at the owner's
  final request; use the latest remote tip rather than an earlier local snapshot.
- Jetson installed application:
  `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`.
- Existing interpreter:
  `/home/super-alex/atlas/venvs/atlas-school-pilot/bin/python`.
- Existing **user** service: `atlas.service`, enabled and active; zero
  unexpected restarts at the latest checks. Do not launch a second runtime.
- Jetson runtime source revision: `f91f82823f7988098fdde6e383cbcc798fd30595`.
  All **187 managed installed files** matched the approved manifest after
  deployment. Later `1535bfa` camera/tool changes were compiled and flashed to
  the XIAO, not installed as a different Jetson runtime.
- Last home SSH: `super-alex@super.local`, address `10.0.0.238`.
  Last camera address: `10.0.0.25`; the app uses `atlas-camera.local`.
  These DHCP addresses are NOT school/static addresses.
- Admin: `http://JETSON_CURRENT_IP:8765/admin`. Preserve existing authentication.

## First priority: school Wi-Fi

Both devices have the supplied **CBAffichages** personal network saved. No
passwords, SSH keys, private headers or private build artifacts belong in Git.

Verified on the Jetson: `ATLAS-personal`, autoconnect **yes**, priority **200**,
`wpa-psk`. The owner's privileged import completed. Original EKA, hotspot and
older enterprise profiles remain. The current working home connection was not
switched. Opaque local checks confirmed the camera's primary header matches
the imported private SSID/password policy; no values were displayed.

The camera's actual combined private build compiled with ESP32 core 3.3.11,
passed cached-build provenance checks and flashed on COM3. It authenticated on
home Wi-Fi. Selection order is personal school, old optional enterprise,
optional home, original hotspot. Visible optional attempts are bounded to 30
seconds. A working fallback is not preempted just because school appears.
Jetson and camera choose independently: fallback does NOT guarantee a shared LAN.

**Not yet verified:** the real school AP was absent at home. SSID/password alone
cannot prove correct authentication or network policy. Do not tell the director
that school connectivity is guaranteed. School IT must provide a compatible
**2.4 GHz** personal network for the ESP32-S3 and permit device-to-device traffic,
mDNS or an approved camera-address configuration, SSH/dashboard access, and
provider HTTPS/WebSocket access. Portals/client isolation can prevent the demo
even when both devices report connected. WPA3-only negotiation was not tested.

At school, first use a local Jetson console (do not risk the only SSH link):

```bash
hostname -I
nmcli -f DEVICE,TYPE,STATE,CONNECTION device status
nmcli -f connection.id,connection.autoconnect,connection.autoconnect-priority connection show ATLAS-personal
systemctl --user is-active atlas.service
```

If necessary and the AP is present, activate from that **local console**:

```bash
sudo nmcli connection up ATLAS-personal
```

This may disconnect SSH. Obtain the actual new address locally. Do not use
`--show-secrets`, print profiles or put passwords in shell arguments. Check the
camera's operational boot/IP using the approved serial workflow if needed;
resetting its USB CDC interface can close the monitor. Once ATLAS reads it,
close direct camera-stream tabs/apps and use the dashboard preview.

## Demo-threatening issues: still OPEN

### 1. Longer answer can change voice (high priority, reproduced)

The owner heard a complete short answer and confirmed correct same-artwork
follow-ups and a switch to another artwork. However, the subsequent detailed
answer test **continued in a different voice**. Do not mark voice consistency
fixed based on the offline suite or the successful short answer.

Privacy-safe health metadata showed last STT Deepgram and last TTS Cartesia
before/after the report. The installed session runner uses
`stream_responses=False`; each ordinary complete answer is sent as one request
with a fixed Cartesia voice ID. The adapter already suppresses local replay
after primary audio starts. No evidence yet establishes a Piper fallback as
the cause; a Cartesia-generated voice/timbre variation or another speech path
must be distinguished, not assumed. No private dialogue/logs/audio were read
or saved. No unverified last-minute voice/provider change was deployed.

Next investigation: reproduce with a short **public synthetic** paragraph and
a longer public paragraph, in the same language, through the unchanged route.
Observe provider/request/context boundaries using privacy-safe metadata only;
compare whole-request synthesis against any announcement/greeting path. Keep
voice/model choices unchanged until evidence supports a change. Add regression
coverage for a confirmed software cause and retest audible long answers,
cancellation and later questions. Synthetic tests cannot certify audible
speaker identity. A temporary local-only voice is a product/voice change:
agree with the owner first, and never call it a fix for Cartesia.

### 2. Camera freshness intermittently drops (high priority, not eliminated)

Earlier stream and five still-image requests timed out; an initial demo start
failed camera/readiness as designed. The camera subsequently recovered, the
owner saw video and Start demo succeeded. Four short observation windows then
passed **25/25, 25/25, 25/25, 24/25** fresh-camera checks (99/100); the missed
sample recovered by the next two-second check. A later probe again reported
camera unavailable, while the service stayed active. This is a recurring risk,
not a clean long-run acceptance pass.

Flashed mitigations: atomic/wrap-safe watchdog state, two-second HTTP wait
limits below the five-second genuine stream watchdog, idle Wi-Fi power saving
OFF. Genuine recovery remains enabled. No readiness bypass, stale-frame limit
increase or speculative still-image fallback was installed. Home antenna was
reported attached and router nearby; repaired camera wiring is owner-reported.
Root cause remains unconfirmed. Separate camera transport/power/RF/reset issues
from Jetson ingestion, with only one direct stream consumer. Do not mask stale
images to get a green readiness indicator. Any wiring inspection is powered off.

## Passed checks and preserved progress

- Combined source/features deployed safely using `scripts/deploy/source_release.py`,
  with native preflight and rollback protection. No generic package upgrade,
  JetPack/L4T change, engine rebuild, service rewrite or secret replacement.
- Listening migration: initial wait 8 s, utterance max 45 s, ordinary pause
  2,000 ms, unfinished-question grace 4,000 ms; pan OFF in both YAMLs.
- Shokz USB input/output detected. Owner heard a deliberate long repeated cue;
  RAM-only spoken microphone levels were non-silent (peak 20,079, RMS 787.8).
  Complete live answer and basic same-artwork/artwork-switch context passed
  by owner confirmation. Deepgram/Cartesia use was confirmed by metadata.
- Existing v6 PyTorch and TensorRT performed GPU inference with correct IDs on
  two public reference images and no detection on a synthetic blank. Seven
  classes loaded. PT/engine/unit hashes remain unchanged (full record below).
- Dashboard/visitor pages and linked assets returned 200; protected status,
  audio and pan routes returned 401 without authentication. No auth weakening.
- Final local suite **3,472 passed, two expected skips**; 465 additional native
  Jetson isolated regressions passed. Ruff/compile/dependencies/secrets/recovery/
  repository layout pass; dashboard JavaScript 97 synthetic checks pass.
- Existing models, museum data, databases, visitor privacy switches, `.env`,
  audio routing, voice IDs and old network profiles were preserved.

These checks establish useful coverage, not flawless physical/cloud operation.

## Other pending tests / possible problems

- Real school authentication, AP band/security, client isolation/portal, mDNS,
  camera-to-Jetson traffic, cloud access and fallback on the actual school LAN.
- Longer camera reset/reconnect and 30–60-minute combined soak; fresh-camera
  YOLO accuracy/false alarms, sustained FPS, latency and enclosure temperature.
- Idle battery consumption/temperature after disabling radio power saving.
- Long answers and multiple languages/accents; hesitant/unfinished questions;
  provider failure/recovery; stop/reset cancellation and clean next visit.
- Artwork A→B→A, explicit named-artwork override, comparisons and typed/spoken
  shared context beyond the basic owner-confirmed follow-up/switch.
- Real multifunction headset button, stop/restart, live dashboard error recovery,
  readable/technical timeline synchronization and privacy controls on hardware.
- Cold boot and approved rollback rehearsal; enabled service is not cold-boot proof.
- Early 0.21-second cue was not heard; a longer repeated cue was. No confirmed
  root cause or cue/routing change. Avoid diagnosing a silent microphone when
  the wearer was not speaking or was entering Wi-Fi details.
- Camera temporary low-resolution diagnostic could not confirm its finally
  restoration over an unavailable control connection. No YAML profile changed;
  normal ingestion requests existing defaults (SVGA/quality 14). Recheck actual
  sensor status when idle/reachable, not by changing a live demo.
- Default visitor-readiness request without language can report language pending;
  that alone is not evidence that an English-configured active visit failed.
- Pan/SG90 mechanical work remains **disabled and paused**, as requested.
  Do not enable PWM, pinmux or attach motor power without supervised power,
  waveform, travel, mount/cable-strain and emergency-stop commissioning.
- Historical unverified enterprise certificate/server assumptions remain
  unresolved; the personal network does not make that older profile secure.
- Private files in ignored OneDrive directories may sync. Git ignore is not
  encryption; never share firmware binaries/build caches/diagnostics or keyfiles.
- No other small defect was confirmed during this arrival session. The items
  above distinguish reproduced bugs from untested scenarios and possible risks.

## Demo preparation / fallback

Before the director arrives, test one complete spoken question/follow-up and
an artwork switch using the actual school network. Keep direct stream clients
closed. If camera readiness fails, do not present stale video as live. If voice
changes, do not promise uninterrupted consistent narration; investigate before
relying on long answers. A controlled fallback demonstration using only already
verified features is preferable to claiming that an untested path is ready.

## Recovery and detailed records

Source backup:
`/home/super-alex/atlas/backups/onsite-20261018/atlas-source-20261018-202611-b165b45b`.

YAML backup:
`/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated/.atlas-onsite-settings-backups/c6b2758c086a4911995e4f48641ea4bd`.

Keep both. Stop the service before any approved rollback, restore compatible
source AND YAML together, verify, then restart. Do not use the old October 4
uploader: it changes model/engine/firmware/unit scope unnecessarily. Never print
`.env`, SSH keys, visitor logs, generated databases or raw media.

See [actual deployment record](../atlas/docs/2026-10-18_JETSON_ONSITE_DEPLOYMENT.md),
[arrival runbook](../atlas/docs/2026-10-18_ONSITE_DEPLOYMENT.md) and
[combined acceptance checklist](../atlas/docs/2026-10-12_COMBINED_RELEASE_AUDIT.md).
