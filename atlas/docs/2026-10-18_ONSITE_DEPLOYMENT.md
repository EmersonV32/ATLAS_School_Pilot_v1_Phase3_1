# October 18 onsite release and arrival runbook

Update: the Jetson source deployment, narrow settings migration, root-only
school Wi-Fi profile installation (autoconnect yes, priority 200), optional
camera home fallback and verified firmware upload have completed. The owner
reports live camera video, successful demo start, a complete spoken answer and
correct same-artwork/artwork-switch context. Deepgram and Cartesia use is
confirmed by health metadata. Four short fresh-frame windows passed 99/100
checks, with the one unavailable sample recovering by the next check. Earlier
camera stalls did occur: long-run stability, extended voice/context scenarios
and school-network acceptance remain pending.
Read the [actual deployment record](2026-10-18_JETSON_ONSITE_DEPLOYMENT.md)
for observed results and rollback locations. The preparation statements below
describe the state before device arrival, not the latest installed state.

## Authority and prepared scope

Candidate branch: `codex/onsite-deployment-ready`, based on the October 12
combined audit (`9c50f87`). This includes all prior conversation/artwork/RAG,
Deepgram hesitation handling, single-provider voice safeguards, long-answer
playback, responsive dashboard, synchronized readable activity and direct SG90
controls. The existing v6 detector and engine are not replaced or rebuilt.
Implementation and regression commit: `f91f828` (local; not pushed).

The owner supplied the new personal-network details and authorized preparation
for both devices and deployment when the teammate brings the hardware. The
details were entered through hidden terminal prompts, not shell arguments.
Private camera settings and a transferable private Jetson profile are now
staged locally. Their contents are not in this document, tests, Git or the
source-only deployment archive. Existing school/hotspot headers are unchanged.

No hardware has been connected, flashed or deployed by this preparation. A
software pass is not physical or cloud acceptance. The motor feature is included
but remains disabled until separate PWM/power/travel commissioning.

## New network and camera changes

- Optional new personal SSID/password primary: no username, enterprise EAP or
  certificate assumptions. Camera preference is personal, then the existing
  optional school profile, optional home fallback, then the original hotspot. Each visible optional
  profile has a bounded authentication attempt; no endless preferred retry.
- Jetson profile `ATLAS-personal` is initially staged with autoconnect OFF and
  priority 200. Explicit local-console activation enables autoconnect only
  after success. Old profiles and their credentials are preserved.
- Camera settings accept WPA2/WPA3 personal; a separate `--security wpa3`
  preparation mode supports an explicitly verified WPA3-only AP. Auto uses
  the compatible personal mode, not an assurance about an unknown AP/adapter.
  Portable passphrases are 8–63 bytes (ASCII for WPA2/auto); 64-hex WPA2 keys
  are accepted only in auto mode. Hidden SSIDs are not part of this selection.
- The XIAO is 2.4 GHz only. IT must enable a compatible band and permit
  device-to-device traffic. SSID/password alone cannot prove radio band,
  security mode, a captive portal or client isolation. Both devices can select
  fallbacks independently; verify the actual shared LAN.
- The audited camera watchdog defect is fixed in source: shared stream state
  is snapshotted under an ESP32 critical section; a newer timestamp cannot
  unsigned-underflow into a false timeout. Real stalls and `millis()` wrap
  still receive recovery. Wi-Fi reconnect timing is also wrap-safe.

References: [Seeed radio/Wi-Fi documentation](https://wiki.seeedstudio.com/xiao_esp32s3_wifi_usage/),
[Espressif S3 Wi-Fi security](https://docs.espressif.com/projects/esp-idf/en/v5.1.2/esp32s3/api-guides/wifi-security.html),
[NetworkManager personal security settings](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nm-settings-nmcli.html).
Keep the earlier enterprise server-verification caveat separate: retaining an
old profile does not resolve its security assumption.

## Before touching devices

Have Jetson power, camera USB **data** cable, Shokz and a local-access option
(screen/keyboard or a known working connection). Wi-Fi activation can disconnect
SSH. Do not rely on an old DHCP address or assume `super.local` resolves.

Private artifacts are under ignored locations. OneDrive may sync them: Git
ignore is not encryption. Do not email/upload/share private headers, keyfiles,
firmware binaries, build manifests or compiler/upload logs. Keep private transfer
files in an owner-only directory, never an open shared `/tmp` file.

## 1. Establish the Jetson link without changing its current network first

At a local Jetson console:

```bash
hostname -I
nmcli -f DEVICE,TYPE,STATE,CONNECTION device status
nmcli -f NAME,UUID,TYPE connection show
systemctl --user is-active atlas.service
```

Use only metadata, not `--show-secrets`, environment dumps or visitor logs.
If old Wi-Fi works, first use it to transfer the approved tools/source archive.
Otherwise use a trusted USB transfer/local console or an already verified wired
path. Do not install system packages or modify JetPack to get connected.

## 2. Install the new Jetson profile locally

The prepared private file on the laptop is
`atlas/.private-network/atlas-personal.nmconnection`. Transfer it privately along
with the **public** `scripts/configure_personal_wifi.py`. For SSH transfer, first
create a 0700 owner-only destination directory; do not put the keyfile in a
world-readable shared directory. Do not display its contents.

At the physical Jetson console, substitute the actual local paths:

```bash
sudo python3 /path/to/configure_personal_wifi.py --target jetson --import-profile /private/path/atlas-personal.nmconnection --activate --local-console
```

The helper refuses activation over an SSH session. It does not restart
NetworkManager or delete old networks. An existing `ATLAS-personal` requires
explicit `--replace`; a replacement retains a private backup and the existing
connection UUID. Imports are constrained to the safe personal-profile policy,
not arbitrary routes or enterprise settings. A UUID belonging to another saved
network is refused. No password appears in a command argument.

After success, obtain the new address locally and reconnect SSH. Remove the
temporary transfer copy after checking the root-only NetworkManager profile
is loaded; retain only the protected intentional recovery copy. The helper
can also prompt locally instead of importing, using `--target jetson`.

## 3. Flash the prepared camera build

Close serial monitors before upload; verify the actual COM port. On Windows,
from `atlas/`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\firmware\xiao_camera\build_and_flash.ps1 -UploadOnly -Port COM3
```

Substitute the actual port. `UploadOnly` requires a prepared build and refuses
changed source, credentials, core version or binaries. It does not silently
upload an old build. If a rebuild is explicitly required:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\firmware\xiao_camera\build_and_flash.ps1 -BuildOnly
```

Builds use an allowlisted staging copy, existing Arduino core and ignored
private cache. Diagnostics stay private. `BuildOnly` does not open a serial
port. The original default compile+upload command remains available.

Read the boot connection result/IP from serial (115200 baud). Resetting the
USB CDC device may end a serial monitor; reopen it after reset. Confirm both
the settings page and a sustained `:81/stream` video, not only a TCP connection.
Once the Jetson is ingesting the stream, use its dashboard preview and close
unnecessary direct browser stream clients to avoid competing consumers.

## 4. Validate and apply the source-only Jetson release

Use `scripts/deploy/source_release.py`, not the October 4 uploader: that older
script rebuilds the engine, packages firmware, removes overrides and replaces
the installed service unit. None is appropriate for this update.

Prepared public source artifact on this laptop:
`ATLAS/deployment-packages/2026-10-18/ATLAS-onsite-source.zip` — 195 allowlisted
files, source revision `f91f828`. Required SHA-256:

```text
0fb1625e230170394db1e0e17cd6acd58002672620cd7c4064434ec86fe854d7
```

Prepare/verify the source ZIP on the laptop only after clean reviewed commits:

```powershell
.\.venv\Scripts\python.exe scripts/deploy/source_release.py build --source-root . --output C:\approved-output\atlas-onsite-source.zip
.\.venv\Scripts\python.exe scripts/deploy/source_release.py verify --archive C:\approved-output\atlas-onsite-source.zip --sha256 VERIFIED_EXTERNAL_SHA256
```

Transfer the public tool/archive over a verified SSH host identity, with its
independently recorded SHA-256. It contains allowlisted runtime/assets, tests,
selected helpers and public validation-only museum fixtures. Those fixtures
are used in disposable validation, not installed over target content/data.
It excludes secrets, configs, firmware, model/engine, installed unit, venv,
databases, logs and generated indexes. Never add private Wi-Fi artifacts to it.

Reconfirm the actual installed paths. The last recorded values, not guarantees:

```bash
ATLAS_APP=/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated
ATLAS_PYTHON=/home/super-alex/atlas/venvs/atlas-school-pilot/bin/python
```

Create an owner-only backup directory outside the application on the **same
filesystem**, then run the transferred tool with absolute verified paths:

```bash
python3 /path/to/source_release.py preflight --archive /path/to/atlas-onsite-source.zip --sha256 VERIFIED_EXTERNAL_SHA256 --root "$ATLAS_APP" --python "$ATLAS_PYTHON" --backup-dir /absolute/approved-backups
python3 /path/to/source_release.py apply --archive /path/to/atlas-onsite-source.zip --sha256 VERIFIED_EXTERNAL_SHA256 --root "$ATLAS_APP" --python "$ATLAS_PYTHON" --backup-dir /absolute/approved-backups --approve-stop-and-replace
```

Preflight validates paths, manifest/hashes, target interpreter/unit and staged
offline regressions before stopping the service. Apply stops the existing user
unit before source replacement. On failure it attempts rollback; incomplete
rollback is explicitly reported and must not be treated as a running release.
An originally stopped service stays stopped unless `--start-if-stopped` was
explicitly approved. No package installation, engine rebuild, unit replacement
or firmware upload occurs in this transaction. Keep the retained source backup.

## 5. Apply the narrow non-secret migration, then verify active values

Use the newly supplied public helper, dry-run first:

```bash
"$ATLAS_PYTHON" "$ATLAS_APP/scripts/prepare_onsite_settings.py" --root "$ATLAS_APP" --camera-host VERIFIED_CAMERA_IP_OR_HOSTNAME
```

With explicit approval and the service stopped, add `--apply`. This backs up
both YAMLs and updates only first-speech wait 8 s, utterance limit 45 s, normal
pause 2,000 ms, unfinished-question grace 4,000 ms, camera-pan disabled and
(if supplied) **both** camera stream/control endpoints. Other values, providers,
privacy flags, voice IDs, audio routes and credentials are not replaced.
Custom override paths require separate review. Start/restart the existing unit
only after approval; do not launch a second manual runtime.

The settings migration is a separate transaction from the source update.
Keep **both** backup sets. If reverting after a successful migration, stop the
service and restore its pre-migration YAMLs before restoring an older source
that may not accept the new settings fields. Never restart a partial restore.
The source tool's automatic rollback covers failures during its own apply;
it is not an automatic rollback of later operator configuration changes.

Environment overrides can still win, especially `ATLAS_CAMERA_SOURCE`. Do not
dump or edit `.env` to troubleshoot. Compare the active dashboard's actual
camera source and approved settings after restart; ask the owner to review a
specific non-secret override if it conflicts. Check numeric IP first, mDNS only
after proving that it resolves and traffic works on this LAN.

For a loopback dashboard, preserve binding/auth and use a tunnel rather than
weakening access controls:

```bash
ssh -N -L 8765:127.0.0.1:8765 super-alex@VERIFIED_JETSON_IP
```

## 6. Required live acceptance before calling the installation ready

Run the full [combined acceptance checklist](2026-10-12_COMBINED_RELEASE_AUDIT.md)
with these priorities:

1. Both devices authenticate on the actual network; SSH, camera controls and
   sustained stream work; client isolation/portal/2.4 GHz checked with IT.
2. V6 detections on real frames; stale-frame rejection and camera reset/recovery;
   verify both camera endpoints and CSI/Argus preview if present.
3. Shokz microphone, cue and whole-answer playback; long local/cloud answers;
   no voice-switch replay; stop/reset cancels old speech and the next visit works.
4. A→B→A artwork changes, named different artwork, same-artwork follow-ups,
   comparisons, typed/spoken shared context and real hesitation/accent examples.
5. All dashboard controls/fault recovery, readable/raw log snapshot pairing,
   quoted-text privacy flags, visitor reset/help and local-only private greeting.
6. Cloud account/model/billing access and real retrieval/response quality.
   HTTP 200 `/health` is process availability, not proof components are ready.
7. Controlled restart/cold boot and combined soak; rehearse approved rollback.

Servo commissioning is separate: direct PWM route, power, signal, safe arc,
mount/cable strain, emergency stop and supervised sweep/jog tests in
[CAMERA_PAN.md](CAMERA_PAN.md). Keep it disabled until those pass; no bare motor
or unverified power connection is automatically enabled by this release.

## Verification record

- Full final suite: **3,466 passed, 2 expected skips**, 311.99 seconds.
  Skips: Windows symbolic-link privilege (a separate deterministic rejection
  test passes) and opt-in real CPU YOLO inference. Existing TestClient
  deprecation and intentional duplicate-ZIP fixture warnings are non-failing.
- Five public synthetic firmware variants compiled/linked with ESP32 3.3.11,
  including real C++ timing/personal-policy assertions. The owner's private
  camera build also completed and passed its source/core/binary validation;
  no port was opened and no device was flashed.
- Six fake-CLI build/upload workflow tests passed in 16.45 seconds. They cover
  build-only, cached upload, changed source/credentials/binary, missing binary,
  missing build and conflicting flags, without any real upload.
- The exact 195-file archive passed external SHA verification, extraction and
  actual staged dependency/compile/offline regression validation in a fresh
  temporary directory. Public museum fixtures were available only inside that
  disposable stage. No existing installation was read or modified.
- Ruff, compilation, dependency consistency, secret scan, recovery bundle,
  repository navigation and whitespace checks passed. The existing dashboard
  JavaScript logic gate passed 97 checks; its interface source was unchanged.

The verification list above describes the original preparation. Latest arrival
source/firmware changes passed **3,472 tests, two expected skips**, and the
actual private combined firmware compiled and flashed. See the deployment
record for 465 additional native Jetson regressions, GPU checks, confirmed
Shokz I/O, live spoken/context checks and the recovered short camera checks.
Physical school AP authentication, longer stability and complete extended acceptance remain
pending. Private build artifacts are intentionally not linked or shared here.
