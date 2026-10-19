# October 18 Jetson source and camera deployment

## Latest acceptance update (October 18 evening)

- **Jetson school Wi-Fi installed:** the owner completed the local privileged
  import. Metadata independently verifies `ATLAS-personal`, autoconnect **yes**,
  priority **200**, and the supplied personal SSID. Existing profiles and the
  active home connection remain intact. Opaque validation confirms that the
  camera's primary network header matches the private imported profile; no
  credential values were displayed. The actual school AP is absent here, so
  school authentication, fallback and inter-device routing are NOT accepted yet.
- **Camera home fallback added and flashed:** the owner privately entered home
  details. The optional home header preserves all three earlier headers. The
  actual combined private ESP32 3.3.11 build compiled and passed UploadOnly
  provenance checks, then flashed successfully on COM3. Boot confirmed home
  Wi-Fi and `10.0.0.25`. The installed Jetson still uses `atlas-camera.local`,
  not that temporary DHCP address.
- **Streaming recovered, short acceptance passed:** earlier isolated stream and
  still-image requests timed out; an earlier readiness sample passed only 12/25
  checks, and the owner's first demo attempt correctly failed readiness. The
  owner subsequently reported working camera video and successful demo start.
  The latest 49.1-second sample passed **25/25** fresh-camera checks, with
  headset/content ready throughout. Three additional approximately 49-second
  samples passed **25/25, 25/25 and 24/25** respectively. The one unavailable
  sample recovered at the next two-second check. Across these four windows,
  fresh-camera readiness was **99/100**; headset/content stayed ready in all
  samples. A later final probe again showed camera ready. The brief recurrence
  means camera stability is NOT defect-free or fully accepted. No readiness
  bypass or speculative snapshot transport was installed.
- **Targeted firmware mitigations:** HTTP send/receive waits are two seconds,
  below the genuine five-second stream watchdog. Idle Wi-Fi power saving is
  disabled to avoid first-frame radio transitions. Genuine stall recovery stays
  enabled; idle battery life and temperature must be measured. The earlier
  shared-state watchdog race fix remains included. Commit: `1535bfa`.
- **Shokz basic I/O confirmed:** the owner heard a deliberate longer repeated
  tone. A subsequent six-second, RAM-only microphone level check while the
  owner spoke produced peak 20,079 and RMS 787.8 (non-silent). Early short cues
  were not heard; early quiet captures occurred before the owner was speaking.
  No raw audio was saved and no device routing/volume was changed. The owner
  then confirmed hearing a complete answer in the actual running demo. A final
  health probe reported last STT **DeepgramSTT** and last TTS **CartesiaTTS**;
  the live speech path was exercised, not just initialized.
- **Final software gate:** **3,472 passed, two expected skips, two non-failing
  warnings**, 506.88 seconds. Ruff, compilation, dependencies, secret/recovery
  and whitespace checks pass. Seven fake-CLI camera workflow tests pass,
  including stale home-header rejection. The final actual private build passed;
  do not describe the interrupted six-variant synthetic compile batch as a
  completed six-variant pass. The earlier five-variant compile is dated evidence.
- **Preservation rechecked:** all 187 installed managed files still match
  `f91f828`; service active/running with zero unexpected restarts; linked assets
  load and protected routes return 401 without authentication. The existing
  unit, models, venv, museum data, databases, privacy/provider/voice choices and
  `.env` were not replaced. Motor commissioning remains paused and pan OFF.

The owner also confirmed correct context for the same-artwork follow-up and
after switching to another artwork and asking who painted it. These basic
spoken/context checks pass by owner observation; no private dialogue/logs were
read. This does not establish every accent/language, hesitation, long-answer,
provider failure or cancellation scenario. Button recovery, cold boot,
sustained whole-answer voice consistency and the longer combined soak remain
acceptance items. No restart was made during the live demo. School LAN
acceptance still requires the school AP, 2.4 GHz support, appropriate personal
security, no portal/client isolation and permitted provider HTTPS access.

The sections below retain earlier arrival observations and rollback details;
this latest update takes precedence over their previously pending statuses.

## Earlier arrival update: camera flashed, headset detected

The owner returned with a USB data cable and resumed camera work. Arduino
discovery identified the ESP32 USB device on COM3. Verified UploadOnly completed
successfully using the prepared private build; no rebuild, credential readback
or compiler/upload log inspection occurred. Serial operational status confirms
the new personal-network selection logic and camera initialization at 800x600,
JPEG quality 14, target 15 fps. Neither the personal school AP nor the prior
enterprise AP was visible here, and the original fallback timed out. No camera
IP or live stream has therefore been verified. The owner was asked to enable
the previously configured hotspot or choose another current test network.
The owner then clarified that only home Wi-Fi is available. Home credentials
have not been provisioned into this camera; adding that network requires private
operator input and must preserve the existing school/hotspot profiles.

The Shokz USB input/output now appears in live visitor readiness. Pulse input,
Pulse output and ALSA output discovery all pass. A short synthetic local cue at
50% software volume completed successfully through the named Shokz output;
audible confirmation is pending the owner. No microphone recording, cloud
round trip or live spoken conversation has been tested in this continuation.
The owner reported not checking the cue, so it is not an audible pass.

The school profile's local sudo import remains pending. The earlier arrival
observations below are retained as dated deployment evidence; camera pause and
headset absence no longer describe the latest physical state.

The owner authorized immediate deployment and testing with the Jetson online.
SSH reached the existing `super-alex@super.local` host at `10.0.0.238`, preserving
strict host-key verification and using the existing SSH identity without reading
or displaying its contents. The installed application remains
`/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`, using its existing venv
and user `atlas.service`.

## Applied release and configuration

- Applied the prepared source-only release, revision
  `f91f82823f7988098fdde6e383cbcc798fd30595`, archive SHA-256
  `0fb1625e230170394db1e0e17cd6acd58002672620cd7c4064434ec86fe854d7`.
- Both native preflight and apply passed isolated dependency, compilation and
  eight-file regression checks before stopping/replacing the existing source.
- The combined conversation/artwork memory, hesitation handling, single-provider
  speech safeguards, long-answer playback, dashboard, readable activity and
  disabled direct-pan implementation are now installed on the Jetson.
- Applied the narrow settings migration in both normal and override YAMLs:
  initial listening wait 8 seconds, maximum utterance 45 seconds, ordinary pause
  2,000 ms, unfinished-question grace 4,000 ms, camera pan disabled.
- Existing camera endpoints, cloud choices, voice IDs, audio routes, privacy
  switches, installed service unit, venv, packages, models and databases were
  not replaced. No `.env`, private keys, visitor logs or raw media were inspected.
- Service was restarted through its existing user unit, not a second runtime.
  Post-migration observations repeatedly show active/running, `NRestarts=0` and
  `ExecMainStatus=0`. This is service stability, not a completed combined soak.

Source rollback backup:
`/home/super-alex/atlas/backups/onsite-20261018/atlas-source-20261018-202611-b165b45b`.

Settings rollback backup:
`/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated/.atlas-onsite-settings-backups/c6b2758c086a4911995e4f48641ea4bd`.

Keep both. The source transaction's automatic rollback covered its own apply,
not the later settings migration. Any later rollback must stop the service,
restore compatible pre-migration YAMLs and source together, and verify before
restarting; never restart a partial restore.

## Observed verification

- All **187 installed managed files** match the approved manifest. Eight public
  validation-only fixture files were not installed over actual museum content.
- Additional native isolated regressions: **465 passed**, one existing
  TestClient deprecation warning, across 16 files covering conversation,
  listening, cloud/local voice adapters, cancellation, activity, dashboard,
  visitor privacy and both motor drivers. They used synthetic fixtures, not
  live microphones, cloud calls or visitor state.
- The first expanded harness run had 464 passes and one failure because the
  source archive intentionally excludes configuration. A prototype-config
  privacy test expected public text-logging switches. Adding an explicit public
  synthetic config only inside the disposable test stage resolved it; all 465
  passed on rerun. Real privacy settings were not loosened or copied into tests.
- Both existing v6 PyTorch and TensorRT backends performed real GPU inference:
  the two curated public Mona Lisa/Great Wave references had the correct IDs;
  a synthetic blank had no detection; both loaded seven classes. This is not
  fresh-camera accuracy or a thermal/performance benchmark. TensorRT emitted
  its engine-portability warning; its unchanged engine hash below and successful
  inference were checked, without rebuilding or modifying the engine.
- Unchanged checkpoint SHA-256:
  `af11b2de376a5c54a1ee11e9765f91ecbf54a1f308a2a82f9106b00a78409731`.
- Unchanged engine SHA-256:
  `6cb18c4a51a80300910808cfba0a9aba4c925a75dd1fa76109b5e04c14d25c17`.
- Unchanged installed service-unit SHA-256:
  `3baed50739465245c99eba94b7840b87e7f4057b15a4c62cfc7ebb66145eb326`.
- Visitor/admin pages, all actual linked CSS/JS/public images and manifest load
  successfully. Protected status, audio and pan routes reject unauthenticated
  requests (401). Laptop-to-Jetson visitor/admin pages also return 200, with
  protected status 401. No authentication policy was weakened.
- Live health reports device mode, YOLO, available vector/FTS retrieval, Gemini,
  Deepgram/Whisper and Cartesia/Piper initialized. Provider readiness does not
  prove cloud billing, a spoken answer or real acoustic quality.

## School network: initial transfer and subsequently completed local import

The supplied personal school-network profile and public import helper were
transferred into the owner-only directory
`/home/super-alex/atlas/onsite-20261018` (0700; private keyfile 0600).
No credential contents were read or printed. Existing network profiles remain.
The Jetson currently uses the working home network; the new school AP was not
visible in the scan. Initially noninteractive sudo required the owner's
password, so no root installation or live Wi-Fi switch was attempted remotely.
The owner subsequently completed both commands below. Metadata now confirms
autoconnect yes and priority 200; the active home connection was not switched.

The owner successfully ran these locally on the Jetson:

```bash
sudo python3 /home/super-alex/atlas/onsite-20261018/configure_personal_wifi.py --target jetson --import-profile /home/super-alex/atlas/onsite-20261018/atlas-personal.nmconnection
sudo nmcli connection modify ATLAS-personal connection.autoconnect yes
```

The second command enables future automatic selection; it does not explicitly
disconnect the working connection now. Verify the saved policy with metadata
only (completed with the expected result):

```bash
nmcli -f connection.id,connection.autoconnect,connection.autoconnect-priority connection show ATLAS-personal
```

Expected: `ATLAS-personal`, autoconnect yes, priority 200. Actual authentication,
fallback and camera-to-Jetson traffic still require the real school network.
Retain the intentional protected recovery copy; remove any temporary transfer
copy only after root installation has been verified. Do not print the profile.

## Earlier physical blockers and remaining next tests

- **Earlier camera pause (subsequently resumed; see update above).** Its repaired wiring was reported,
  but the USB cable has no data capability. No COM port was detected; no firmware
  upload occurred. The verified private build remains ready for UploadOnly once
  the owner supplies a data cable and explicitly resumes camera work.
- **Earlier Shokz absence (subsequently detected; see update above).** PulseAudio and ALSA
  expose onboard/HDMI audio only. Live readiness correctly reports headset and
  camera unavailable, plus visitor language pending. Connect the Shokz USB
  adapter/headset before actual microphone, cue, long-answer, voice continuity,
  stop/reset and button acceptance. No recorded audio was inspected or saved.
- Motor feature stays disabled. No PWM, pinmux, power or mechanical
  commissioning occurred. The disabled motion/EV3 adapter's `MockHardware`
  health label does not mean the device-mode retrieval or YOLO are mocked.
- Still required: actual school authentication and fallback; a sustained camera
  stream/reset/reconnect test and fresh-camera YOLO evaluation; longer voice,
  hesitation, cancellation and artwork A→B→A exercises beyond the confirmed
  complete live answer/same-artwork follow-up/artwork switch; dashboard live
  faults/activity/button synchronization; cold boot and controlled 30–60-minute
  combined soak; separate motor commissioning. Use the [arrival runbook](2026-10-18_ONSITE_DEPLOYMENT.md)
  and [combined acceptance checklist](2026-10-12_COMBINED_RELEASE_AUDIT.md).

The source deployment succeeded and the owner started a live demo; full
school-network and sustained physical acceptance are **not** yet complete.
No Git push or promotion to `main` occurred.
