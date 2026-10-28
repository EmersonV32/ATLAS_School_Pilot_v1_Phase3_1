# Current state

## Full wake introduction deployment — 2026-10-28

Latest installed source: `228f4da` from `codex/full-wake-introduction`.
The optional named greeting keeps the complete guide introduction; English/
French finish the role/help explanation before an interest question. Both
proactive camera invitation paths require successful current-visit introduction
and recheck queued visit IDs. Names remain private/local and ephemeral.

All 203 managed files match the release manifest. Local guarded suite: 4,537
passed, three skipped, independently 4,540 collected. Installed mocked suite:
306 passed after documented native test-port isolation. Service active/running,
NRestarts 0, ExecMainStatus 0; public HTTP 200 and protected HTTP 401. Boot ID
and excluded-file metadata unchanged; rollback kept. Main unchanged.
See [release and retest steps](../atlas/docs/2026-10-28_FULL_WAKE_INTRODUCTION.md).
Start a fresh visit for the once-per-visit greeting. Full audible playback and
name pronunciation still require the owner's headset check.

## Interactive FAQ deployment — 2026-10-28

The latest owner-authorized source-only test release is `d7ecce7`, from
`codex/interactive-fast-faq`; it supersedes the earlier release below. All 202
managed files match the archive; 3,334 new-feature mock tests pass natively.
Local full gate: 4,506 passed, three skipped, independently 4,509 collected.
Service active/running, NRestarts 0, ExecMainStatus 0, public health HTTP 200,
protected routes HTTP 401; boot ID and excluded-file metadata unchanged.
Rollback retained. Main was not changed.
See [the release record](../atlas/docs/2026-10-28_INTERACTIVE_FAQ_TEST_RELEASE.md).

This release adds varied prepared invitations and local Yes/Oui continuations,
more complete French question forms, a conservative 600 ms exact-final FAQ
silence path with resumed-speech coverage guards, and immediate PCM flushing.
Long/ambiguous questions retain the deeper path and existing silence policy.
Timing traces measure player input, not headset audibility; under-two-second
audible acceptance and live model interaction remain with the owner.

## Test-branch deployment — 2026-10-28

The owner-authorized source-only release `a1a8154` is installed on the Jetson
from `codex/faq-wake-french-dates-runtime`, with no main promotion. All 200
installed managed files match its manifest; 2,994 new-feature mocked tests
passed natively. Service active/running, public health HTTP 200, zero unexpected
restarts, unchanged boot ID and excluded-file metadata; rollback is retained.
See [the deployment record](../atlas/docs/2026-10-28_TEST_BRANCH_RELEASE.md).
The release includes FAQ bypass, explicit private named introduction, French
spoken dates, recommendation policy and acceptance-to-recommended-artwork
routing. Physical/audible/model-quality acceptance remains with the owner.
The local-only notes below are historical stages superseded by this release.

## Local review pending — 2026-10-27

The uncommitted descendant `codex/faq-wake-french-dates-runtime` contains the
requested prepared-answer matching/pipeline fixes, explicit Hey Atlas / Bonjour
Atlas introductions, private dashboard-name greeting, and French spoken dates.
See [the change and Jetson checklist](../atlas/docs/2026-10-27_FAQ_WAKE_FRENCH_DATES.md).
No main promotion, push, deployment, restart, or fresh physical acceptance is
part of this local work. The deployment observations below keep their dates.
The new behavior intentionally removes automatic session-start introductions;
ordinary camera-free questions remain available before a greeting.

## Current continuation — 2026-10-26

Read the [two-week teammate handoff](2026-10-26_TEAMMATE_HANDOFF.md),
[new Codex prompt](NEW_CODEX_PROMPT.md), and
[deployment/rollback runbook](DEPLOYMENT_RUNBOOK.md) first.

- Continue from `codex/camera-offline-demo-2026-10-25`, active source `atlas/`.
  Later working fixes are not promoted to `main`. This handoff changes no
  live device state.
- Last verified runtime deployment: `4b2233c` on October 25; `d7b6ded` records
  that deployment. Later handoff commits are documentation/tooling, not a new
  runtime deployment. All 195 installed managed source files matched the
  release; the user service was active with zero unexpected restarts.
- Latest local runtime gate before this handoff: **3,789 passed, two skipped**
  across all 55 test files; 182 focused tests passed. Native pronunciation
  tests: 36 passed. These are dated results, not today's hardware acceptance.
- October 26 handoff gate: **3,791 passed, two skipped** across the same 55
  files, plus 25 focused checks, 106 synthetic admin JavaScript checks and
  42 synthetic visitor keyboard transitions. Recovery, navigation, lint,
  dependencies, compile, obvious-secret and whitespace checks passed.
  No live Jetson action or fresh physical acceptance was performed.
- Cartesia payloads normalize standalone `ATLAS` to `Atlas`, retaining the
  selected voice/model/language and uppercase UI branding. The owner's
  **audible pronunciation check remains pending**. See the
  [pronunciation record](../atlas/docs/CARTESIA_NAME_PRONUNCIATION.md).
- The same release includes the visitor navigation fix (`38e2c69`, shell v30),
  conversation/wake-pause fixes (`5d577d9`), and voice recovery (`f90bf48`).
  Provider timbre consistency still needs audible acceptance.
- Primary wearable camera is offline (owner reports damaged BAT+ contact).
  Camera-free conversation can start; capture still requires fresh frames.
  Configured cloud services still require internet. Separate CSI preview is
  independent and needs a fresh physical check when that feature is used.
- **SG90 pan is PAUSED, NOT WORKING, and DISABLED.** Servo-side idle power
  (5.1 V) and signal-wire continuity were checked, but there has never been
  successful movement or a verified waveform. Do not repeat motor tests or
  bypass safety flags. See the current handoff's hardware section.
- October 26: owner reports the Jetson connected to the teammate's Windows
  mobile hotspot sharing school Wi-Fi, at `192.168.137.193`. DHCP may change
  this. Direct school discovery/root cause is unresolved; home Wi-Fi previously
  worked. No hardware fault or regulatory fix is established.

The present teammate can authorize scoped work during the owner's absence.
Deployment, restarts, network changes, and physical outputs still need a
coordinated operator window. Credentials/admin codes stay outside Git.

## Earlier snapshots — historical evidence

The material below retains earlier observations and superseded candidate
instructions. Earlier installed revisions, counts, branch names, and pending
checks describe their original date; they do not override the summary above.
Source status date of the following snapshot: 2026-10-25.

**Read [October 25 voice recovery and greeting update](../atlas/docs/2026-10-25_VOICE_AND_GREETING.md),
then [October 25 camera-free deployment](../atlas/docs/2026-10-25_CAMERA_FREE_DEMO.md)
first, then the [school director demo / teammate handoff](2026-10-18_SCHOOL_DEMO_HANDOFF.md).**
The camera is physically offline (owner reports damaged BAT+ contact). Voice
demo start no longer requires a camera; the owner confirmed that it starts.
The voice-change problem recurred today and affects all languages, not just
French. It remains OPEN. School Wi-Fi is saved on both devices, but actual
school authentication and LAN acceptance remain unverified.

## October 25 latest deployment and acceptance

Latest voice/greeting implementation: `f90bf48`. It fixes permanent fallback
after a transient Cartesia failure and serializes whole-answer speech; both
admin and visitor starts now queue an automatic selected-language introduction
before listening. Private optional names stay local-only. Native preflight
passed; **3,593 tests passed, two skipped**, and source apply succeeded.
All 189 installed files match; service/headset/AI/speech are healthy. Exact
evidence and rollback backup belong to the linked latest record.
Provider-internal timbre drift is not proven fixed by these client safeguards.

Current work branch: `codex/camera-offline-demo-2026-10-25`; installed source
revision: `d9b062b3868cd4c4a5122a1cf29d3bc5f0f609ab`. Main is unchanged.
The existing user service was updated with a reversible source-only release.
All 188 managed files match; service active/running with zero unexpected
restarts, headset/AI/retrieval ready. Camera readiness is truthfully degraded,
not a demo blocker. Capture remains unavailable without fresh camera frames.
Named-artwork questions and staff manual artwork context do not need a camera.

Software checks: **3,480 passed, two skips**, Ruff/dependency/secrets/recovery
and whitespace gates passed. Synthetic dashboard browser QA: 35 layouts,
32 actions, 11 failure/recovery scenarios, 2,727 contrast checks, zero unexpected
errors. Camera-offline visitor flow: 42 keyboard transitions at 1024x768,
reduced motion, no visitor cookies/storage/IndexedDB, zero browser errors.
These are not audible or motor acceptance claims.

The owner first reported demo start failure, then corrected that report:
the demo works. French voice variation was reported, then clarified to affect
all languages. Last-used health metadata still identifies Cartesia, not proof
of the cause or a provider switch. The owner is restarting ATLAS to retest;
no speculative voice/provider/config changes or second restart were made.
Temporary recovery after restart is not a permanent fix.

Direct-SG90 dashboard/controller software is installed but motor output stays
OFF. Read-only discovery finds both supported PWM controllers with user
access. Header pinmux/waveform, servo power, calibration and CSI preview under
load remain unverified; the owner has not identified a suitable supply.
See [camera pan setup](../atlas/docs/CAMERA_PAN.md). Do not enable EV3, human
tracking, sentence TTS or privacy-sensitive logging just to remove inactive
labels. Existing hardware and safety prerequisites still apply.

The sections below retain dated historical evidence; their earlier
"not deployed" descriptions do not override this latest deployment record.

## Maintained version and source

- Maintained baseline: `main`; current deployment-work checkout:
  `codex/onsite-deployment-ready` (published to GitHub; not promoted to `main`). The one active
  implementation is [atlas/](../atlas/).
- Package: ATLAS School Pilot v1, Python package version `0.1.0`; the repository
  name retains Phase3_1, but the runtime includes later integrated work.
- Active detector: seven-class YOLO26 Nano **v6**, checkpoint SHA-256
  `af11b2de376a5c54a1ee11e9765f91ecbf54a1f308a2a82f9106b00a78409731`.
  "v6" is the detector/dataset version, not the application package version.
- [Branch guide](BRANCHES.md): four retained historical/experimental branches
  contain unique work and are not automatically integrated or deployed.
- [Cleanup record](2026-10-11_REPOSITORY_CLEANUP.md): removed duplicates,
  validation results and recovery. No private data or device state is in Git.

October 11 source also adds early duplicate-start checks before device adapter
loading. These reduce ordinary competing launches, not a race-free singleton
guarantee, and have not been deployed to the offline Jetson. Final clean-checkout
Windows suite and Linux recovery gate each passed 3,081 tests with one expected
skip and the existing non-failing deprecation warning. Maintained lint,
dependency, secret, recovery and navigation checks pass. The portable
deployment-package fix covers both present and missing `TEMP` and verifies
staging cleanup. See the cleanup record for exact CI evidence.

The runtime includes artwork capture, bounded conversational context, museum
retrieval and general Gemini fallback, configurable local/cloud speech,
multilingual visitor setup, staff controls, headset-button handling and
readiness/session/event storage. See [system architecture](architecture/SYSTEM_ARCHITECTURE.md).

## October 18 onsite deployment — demo started, school acceptance pending

The owner brought the Jetson online and authorized immediate deployment.
The prepared `f91f828` source-only release is now installed in the existing
application and user service. The narrow listening migration was applied with
YAML backups and pan disabled. Native expanded regressions: **465 passed**;
187 installed source files match the release; both unchanged v6 backends passed
real GPU inference on public references/blank input. Service is active with no
unexpected restarts; actual dashboard assets and LAN/auth checks pass.

The owner completed the privileged school personal-profile import. Metadata
confirms `ATLAS-personal`, autoconnect **yes**, priority **200**; old networks and
the active home link remain. Opaque checks confirm matching primary camera
network settings. The school AP is not visible here, so authentication,
fallback and school inter-device/provider traffic remain untested.

The owner privately configured optional camera home Wi-Fi. The actual combined
private firmware compiled and flashed at COM3, preserving school/hotspot
profiles. Home boot IP was `10.0.0.25`; the installed Jetson still uses mDNS.
Commit `1535bfa` adds the home fallback and bounded HTTP timeouts, and disables
idle Wi-Fi power saving (battery/thermal measurement due). Earlier live camera
stalls and a blocked demo occurred; subsequent recovery passed **25/25** fresh
frame checks over 49.1 seconds. Three additional windows passed 25/25, 25/25
and 24/25: **99/100 total**, with one brief unavailable sample recovering at
the next two-second check. Final probe again shows camera ready. The owner
reports camera video and a successfully started demo; the brief recurrence
means sustained camera stability remains open.

Shokz audible repeated-tone output and a RAM-only spoken microphone-level test
passed. The owner subsequently confirmed a complete live spoken answer and
correct context for same-artwork follow-ups and an artwork switch. Last-used
provider metadata confirms Deepgram and Cartesia exercised. Extended
long-answer/hesitation/cancellation, A→B→A, button and cold-boot acceptance
remain due; no audio routes or provider/voice IDs were changed.
Final local software gate: **3,472 passed, two expected skips**,
plus lint/compile/dependency/secret/recovery checks. Pan remains disabled;
mechanical commissioning is paused. See the [deployment record](../atlas/docs/2026-10-18_JETSON_ONSITE_DEPLOYMENT.md)
for exact evidence and both rollback backups. Main is unchanged. At the owner's
final request, the deployment branch and teammate handoff were pushed to GitHub.

### Earlier October 18 preparation evidence

Latest local candidate: `codex/onsite-deployment-ready`, based on the combined
audit at `9c50f87`. The owner supplied personal Wi-Fi details; a new ignored
camera header and private transferable Jetson profile were prepared via hidden
input. No actual credentials are in Git or the source archive. Old profiles are
preserved. Personal network is preferred before the previous fallbacks.
Public implementation/regression commit: `f91f828` (local, not pushed).

The XIAO false-stall watchdog race and reconnect clock-wrap handling are fixed
in source. Five synthetic ESP32 3.3.11 firmware variants compiled. Actual Wi-Fi
band/security/client isolation, flash and hardware acceptance remain pending.
Direct-pan controls are included but motor activation remains disabled until
separate physical commissioning. Main and installed hardware are unchanged.

Final software gate: 3,466 passed, two expected skips (Windows symlink privilege
and opt-in real CPU inference), with the existing TestClient and intentional
duplicate-ZIP fixture warnings. All lint, dependency, compilation, secret,
recovery, navigation and whitespace gates pass; dashboard JavaScript: 97 checks.
The private camera build is cached for verified UploadOnly; no device flashed.
The public 195-file source archive is prepared outside Git under
`ATLAS/deployment-packages/2026-10-18/ATLAS-onsite-source.zip`, SHA-256
`0fb1625e230170394db1e0e17cd6acd58002672620cd7c4064434ec86fe854d7`.
Its exact staged validation also passed independently; physical readiness is
still pending and must not be inferred from an HTTP 200 or a software pass.

Use the [October 18 arrival/deployment runbook](../atlas/docs/2026-10-18_ONSITE_DEPLOYMENT.md)
for the private cached camera upload, strict source-only archive/update,
rollback, approved pause/camera-endpoint settings migration and live test order.
Do not run the old model/firmware/unit-changing uploader for this update.

## October 12 combined release audit — not deployed

The latest local candidate is `codex/combined-release-audit`, based on
`codex/jetson-direct-camera-pan` at `fcfbd02`. It combines all October 11–12
workflow, dashboard, readable activity and direct-pan work below, with audit
fixes for stale typed artwork/current-view context, stale camera frames,
incomplete speech reported as successful, activity-write failures, late
protected dashboard responses, visit-stop speech cancellation and the fixed
30-second local-playback cutoff for long answers. The new
listening limits are now visible/validated in protected settings.
The reviewed implementation/regression commit is `da8dbca` (local).

Final combined gate: 3,345 passed, one opt-in real-YOLO skip and the existing
non-failing TestClient deprecation warning. Focused voice tests: 31 passed;
JavaScript: 97 checks; headless Chrome: 35 layouts, 30 control checks, 10
failure/recovery scenarios, 2,725 contrast checks and no unexpected errors.
Visitor browser regression: 33 keyboard transitions at 1024x768 with reduced
motion and no visitor browser storage/cookies. Lint, compile, dependencies,
secrets, recovery, repository navigation and whitespace gates passed.

Read the [combined audit and online acceptance checklist](../atlas/docs/2026-10-12_COMBINED_RELEASE_AUDIT.md)
first when the devices return. It records software evidence, safe source-only
deployment boundaries and all remaining real-device/cloud tests. This is not
a claim of a flawless physical installation: the existing XIAO watchdog timing
defect remains open and requires separately approved firmware work. Pan remains
off; motor commissioning is deferred. No push, merge to `main`, deployment,
package, firmware or live service/configuration change occurred.

## October 11 conversation/listening work — not deployed

`main` remains the maintained baseline. The local feature branch
`codex/conversation-listening-stability` adds shared typed/spoken visit memory,
explicit artwork transitions, consistent FAQ/RAG/Gemini subjects and Deepgram
hesitation/long-question handling. See the
[workflow record](../atlas/docs/2026-10-11_CONVERSATION_LISTENING_STABILITY.md)
for exact bounds and acceptance steps. These changes have not been promoted to
`main`, pushed or deployed; the devices were offline. They do not resolve the
separate camera-stream watchdog or school-network acceptance risks below.
The final local workflow suite passed 3,146 tests with one expected skip; lint,
dependency, secret, compilation, recovery and navigation checks pass. Synthetic
visitor browser QA passed 33 keyboard transitions at 1024×768 with reduced
motion and no visitor state stored in the browser.

The deferred SG90 camera-pan work is retained separately on
`codex/arducam-sg90-pan`; it is not implicitly integrated into this workflow
branch. Hardware/controller/power choices and physical testing remain deferred.

## October 12 private dashboard redesign — not deployed

October 12 local source work: `codex/dashboard-redesign` builds on the workflow
branch with a fully redesigned private operations dashboard, persistent fault
reporting, responsive controls and privacy-safe spoken-interaction outcome
metadata. Visitor assets and dialogue/playback behaviour remain unchanged.
See [the dashboard record](../atlas/docs/2026-10-12_DASHBOARD_REDESIGN.md) for
verification and physical acceptance. This branch is not pushed, promoted to
`main` or deployed; it does not include the separate SG90 hardware feature.
Final software checks passed: 3,159 tests with one expected skip, 49 synthetic
dashboard JavaScript checks, 35 browser layouts, 17 control actions and eight
failure/recovery scenarios. A fresh visitor browser regression passed 33
keyboard transitions at 1024×768. Physical acceptance still remains due.

## October 12 readable activity — not deployed

Local branch `codex/readable-live-activity` builds on the dashboard redesign
with a plain-language activity timeline and a single shared snapshot for
readable and technical output. It covers listening/questions/responses,
camera context, headset button presses and failures, with the existing
text-logging privacy switches preserved. Local FAQ response observations are
opt-in; conversation and playback behaviour are not changed. See
[the activity record](../atlas/docs/2026-10-12_READABLE_ACTIVITY.md) for exact
sync bounds, privacy handling and verification. No push, `main` promotion,
hardware deployment or SG90 integration has occurred.
Final local checks passed: 3,246 tests with one expected skip, 62 JavaScript
checks, 35 browser layouts, 18 control actions, nine failure/recovery scenarios
and an actual synchronized export. Visitor QA again passed 33 keyboard
transitions at 1024x768. Physical acceptance remains outstanding.

## October 12 direct SG90 camera pan - not deployed

The user confirmed Seeed reComputer Super / Jetson Orin NX 16 GB (J4012).
Local branch `codex/jetson-direct-camera-pan` now combines the latest readable
activity/dashboard/conversation work with the earlier pan controller and a
direct Linux hardware-PWM driver. No PCA9685 is needed for this backend.
The old `codex/arducam-sg90-pan` branch and its PCA-only deployment patch are
historical proposals, not the current combined release or deployment authority.

See [camera pan setup](../atlas/docs/CAMERA_PAN.md): J10 physical pin 32 / PG.06
/ PWM7 is the default route, with pin 15 / PWM1 supported as a verified
alternative. The Super wiki/schematic were checked against NVIDIA's SoC PWM
map; the actual installed pinmux/waveform still needs verification. GPIO drive
is weak, so buffer-free signal compatibility is not proven. J10's documented
5 V capacity alone does not prove suitable motor startup/stall power.

Pan is off by default. Device movement additionally requires explicit PWM,
power and travel confirmations. Private dashboard controls sit beside the
CSI preview; faults appear on the global issue board. Manual jog expires on
lost renewal, while explicitly requested sweep/target motion may continue
after a network disconnect. Safety clear does not restart motion. The existing
service owns the motor; no camera/audio/model/provider/service/boot settings
were changed on hardware. Human tracking remains future work.

Final local gate passed 3,323 tests, one expected skip and the existing
non-failing deprecation warning; 81 JavaScript checks; 35 browser layouts,
29 control requests, 10 failure/recovery checks and 2,717 contrast checks.
Ruff, compile, dependencies, secrets, recovery and whitespace checks passed.
Visitor QA again passed 33 keyboard transitions at 1024x768, with reduced
motion, no browser errors and no visitor browser storage/cookies.
No push, `main` promotion or deployment occurred. The servo waveform, safe
power, full physical travel, mount/cable strain and voice/preview under motor
load must be supervised on the real offline hardware before enabling pan.

## Previous recorded deployment: October 4

At the user's explicit request, v6 and five runtime fixes were deployed to the
Jetson on 2026-10-04 at 18:38 EDT. The service was active in device mode with a
newly built and verified 416 FP16 TensorRT engine, retrieval/speech readiness and
fresh camera/headset readiness signals. Native tests: 3,002 passed, two expected
skips. Original device config/unit hashes were unchanged and a durable pre-v6
rollback backup was preserved.

Read [the deployment record](../atlas/docs/2026-10-04_JETSON_V6_DEPLOYMENT.md)
for exact evidence, rollback and outstanding acceptance. The installed root
remains `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`.
No October 11 deployment, package installation, service or firmware change is
part of repository cleanup. The earlier
[local integration record](../atlas/docs/2026-10-04_V6_LOCAL_INTEGRATION.md)
describes CPU preparation, not the later deployment.

## School Wi-Fi preparation and operator reports: October 5 onward

The source supports optional school PEAP/MSCHAPv2 under the owner's unverified
authentication assumption. The camera tries a visible school network first
with a 30-second authentication window, then the unchanged hotspot. The Jetson
helper stages an inactive priority-100 school profile; the documented local
console step enables it and sets hotspot priority 50. Neither device preempts
a working hotspot. They authenticate independently and may choose different
networks, so fallback alone does not prove camera-to-Jetson reachability.

All three synthetic firmware variants compiled on ESP32 core 3.3.11. The owner
reported configuring/flashing camera credentials and setting Jetson profiles;
these reports are not successful school authentication evidence. The reported
hotspot Jetson address was `172.20.10.3/28`, gateway `172.20.10.1`, and Avahi
was active under hostname `super`. Treat addresses as observations, not a
guaranteed reservation. Phone-terminal mDNS connection was not confirmed.

School authentication, client isolation and fallback remain physically
untested. The school certificate/server identity is unverified; the helper's
explicit risk acceptance does not make that safe. Keep actual credentials in
ignored private storage. Use [school setup](../atlas/docs/SCHOOL_WIFI_SETUP.md).

## Open physical risks and acceptance

- Camera live-stream timeouts/restarts occurred during October 18 arrival.
  The watchdog race fix and bounded-HTTP/radio mitigations are now flashed;
  subsequent short fresh-frame checks and owner demo start passed. A longer
  controlled soak/reset/reconnect check is still due; root-cause elimination
  and battery/thermal performance are not established by the short pass.
- Fresh seven-class camera evaluation, false-alarm review, live voice/headset
  flow, sustained thermal/FPS and end-to-end timing remain due.
- School authentication and device-to-device traffic must be tested at school.
- Hotspot connectivity and phone SSH/mDNS must be verified on the actual
  devices; laptop tests cannot prove them.
- Cloud provider account/billing availability must be checked before a demo.

Follow [the validation checklist](VALIDATION_CHECKLIST.md). Do not interpret
automated tests, branch renaming or old readiness observations as physical
acceptance.

## Historical evidence

[August Jetson status](jetson/JETSON_RUNTIME_STATUS.md) records earlier 280-test
validation, 800x600 camera samples, hot-plug recovery and Chinese voice tests.
Its then-current branch/provider statements are dated evidence, not today's
source authority. [October 4 continuation](2026-10-04_NEW_CHAT.md) retains model,
hardware and design context; read this current summary first.
