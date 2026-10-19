# October 18 Jetson source deployment — camera paused

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

## School network: transferred, local privileged import still pending

The supplied personal school-network profile and public import helper were
transferred into the owner-only directory
`/home/super-alex/atlas/onsite-20261018` (0700; private keyfile 0600).
No credential contents were read or printed. Existing network profiles remain.
The Jetson currently uses the working home network; the new school AP was not
visible in the scan. Noninteractive sudo requires the owner's password, so no
root profile installation or live Wi-Fi switch was attempted.

The owner was asked to run these locally on the Jetson:

```bash
sudo python3 /home/super-alex/atlas/onsite-20261018/configure_personal_wifi.py --target jetson --import-profile /home/super-alex/atlas/onsite-20261018/atlas-personal.nmconnection
sudo nmcli connection modify ATLAS-personal connection.autoconnect yes
```

The second command enables future automatic selection; it does not explicitly
disconnect the working connection now. Verify the saved policy with metadata
only before calling school setup complete:

```bash
nmcli -f connection.id,connection.autoconnect,connection.autoconnect-priority connection show ATLAS-personal
```

Expected: `ATLAS-personal`, autoconnect yes, priority 200. Actual authentication,
fallback and camera-to-Jetson traffic still require the real school network.
Retain the intentional protected recovery copy; remove any temporary transfer
copy only after root installation has been verified. Do not print the profile.

## Physical blockers and next tests

- **Camera explicitly paused by the owner.** Its repaired wiring was reported,
  but the USB cable has no data capability. No COM port was detected; no firmware
  upload occurred. The verified private build remains ready for UploadOnly once
  the owner supplies a data cable and explicitly resumes camera work.
- **Shokz absent from the Jetson's current audio devices.** PulseAudio and ALSA
  expose onboard/HDMI audio only. Live readiness correctly reports headset and
  camera unavailable, plus visitor language pending. Connect the Shokz USB
  adapter/headset before actual microphone, cue, long-answer, voice continuity,
  stop/reset and button acceptance. No recorded audio was inspected or saved.
- Motor feature stays disabled. No PWM, pinmux, power or mechanical
  commissioning occurred. The disabled motion/EV3 adapter's `MockHardware`
  health label does not mean the device-mode retrieval or YOLO are mocked.
- Still required: local Wi-Fi import/policy verification; school authentication
  and fallback; camera flash/stream/reset/reconnect and fresh YOLO frames;
  headset and real cloud voice/context/artwork A→B→A exercises; dashboard live
  faults/activity/button synchronization; cold boot and controlled 30–60-minute
  combined soak; separate motor commissioning. Use the [arrival runbook](2026-10-18_ONSITE_DEPLOYMENT.md)
  and [combined acceptance checklist](2026-10-12_COMBINED_RELEASE_AUDIT.md).

The source deployment succeeded; the complete physical installation is **not**
yet accepted. No Git push or promotion to `main` occurred.
