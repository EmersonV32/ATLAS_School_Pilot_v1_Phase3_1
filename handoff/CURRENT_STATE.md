# Current state

Source status date: 2026-10-12. Physical observations below retain their actual
dates; repository cleanup is not a hardware deployment or a fresh health check.

## Maintained version and source

- Branch: `main`. The one active implementation is [atlas/](../atlas/).
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

## Latest recorded deployment: October 4

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

- Camera live-stream timeouts/restarts were reported. The separately diagnosed
  stream-watchdog timing race remains unpatched; repository cleanup does not
  claim to fix it.
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
