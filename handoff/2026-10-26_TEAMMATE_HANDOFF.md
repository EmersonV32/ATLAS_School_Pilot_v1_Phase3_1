# Teammate takeover — October 26, 2026

This is the current operational handoff for the owner's two-week absence.
The on-site teammate is the human operator and can approve scoped work; do not
wait for the absent owner for ordinary decisions the teammate can make.
General responsibility is not blanket approval for deployments, motor motion,
firmware flashes, credential changes or destructive operations.

Read [START_HERE](START_HERE.md), both repository/application `AGENTS.md` files,
and [the deployment runbook](DEPLOYMENT_RUNBOOK.md). Give a new Codex
[this starting prompt](NEW_CODEX_PROMPT.md). Older dated reports are evidence,
not instructions to overwrite the current installation.

## 1. The right repository and branch

- Repository: `https://github.com/EmersonV32/ATLAS_School_Pilot_v1_Phase3_1`.
- Current continuation branch: **`codex/camera-offline-demo-2026-10-25`**.
- Only active implementation: **`atlas/`** at the repository root.
- `main` remains the release/Pages baseline, but has NOT been promoted with the
  latest October 25 operating fixes. Do not start this takeover from stale
  `main`, an archive, another nested Git repository, or an older feature branch.
- Work on a `codex/` branch; never force-push or merge into `main` without an
  explicit human request and the full gate. Do not reset another person's work.
- `codex/arducam-sg90-pan` preserves four older local-only development commits
  through `bbf934e`. It is historical recovery material, not the current
  deployment source; the current branch contains the later direct-PWM work.

For a NEW directory only:

```bash
git clone --single-branch --branch codex/camera-offline-demo-2026-10-25 https://github.com/EmersonV32/ATLAS_School_Pilot_v1_Phase3_1.git ATLAS-teammate
cd ATLAS-teammate
git status --short --branch
git log -5 --oneline
```

For an existing checkout, inspect its branch and dirty files BEFORE fetching,
switching or pulling. Do not overwrite an inherited checkout with the command
above. Laptop checkout state, GitHub HEAD and installed Jetson source are three
different things; record all three when releasing.

## 2. What was actually verified

| Item | Latest evidence and limit |
| --- | --- |
| Jetson source | Last verified installed revision: `4b2233c3d4961cbd8d929f27198cab727b034ba3`, October 25. Later documentation commits do not mean another runtime deployment. |
| Application | Existing user `atlas.service` was active/running, exit status 0, zero unexpected restarts; public health/UI passed. Recheck today rather than treating this as live telemetry. |
| Local software gate | 3,789 passed, 2 skipped over all 55 test files at the pronunciation release; 182 focused speech/identity/privacy tests. Later handoff-only validation is recorded with this handoff's commit. |
| Native pronunciation gate | All 195 installed managed files matched the 203-file source archive; 36 new fake-transport tests passed on the Jetson. This does not prove the sound produced by Cartesia. |
| Visitor navigation | Installed revision `38e2c69` underneath the pronunciation fix; shell version 30. Synthetic 1024×768/reduced-motion QA exercised delayed startup, 500 ms saves and 42 keyboard transitions. Physical one-tap acceptance still belongs to the operator. |
| Conversation | Installed `5d577d9` work: silent wake/hesitation pauses, simple child answers, contextual word definitions, one session introduction. Real accent, long-answer and cloud-quality acceptance remains due. |
| Networking, October 26 | Human reports successful Jetson connection through a Windows laptop mobile hotspot sharing school Wi-Fi. Reported SSH IP: `192.168.137.193`. This is DHCP, not a reservation; this handoff did not independently recheck that school link. |
| SG90 pan | **PAUSED / NOT WORKING / DISABLED.** No visible servo movement was ever demonstrated. A completed PWM command is not a successful motor test. |

Latest pronunciation release archive SHA-256:
`9bc56e025588679f662679cd90b17d8b3ec69e892bd4b86469a35dd9ff99f421`.
It contains public source/tests plus validation-only public fixtures, not private
settings, service units, live data or a device-specific TensorRT engine.
See [pronunciation evidence](../atlas/docs/CARTESIA_NAME_PRONUNCIATION.md),
[navigation evidence](../atlas/docs/VISITOR_NAVIGATION_ACCEPTANCE.md), and
[conversation evidence](../atlas/docs/CONVERSATION_LANGUAGE_ACCEPTANCE.md).

No live Jetson action, firmware flash or new physical acceptance is performed
just by preparing this October 26 handoff. Ask the teammate about any work
performed after the last verified release.

## 3. Device identity, access and daily operation

| Property | Value |
| --- | --- |
| Hardware | Seeed reComputer Super J401 / Jetson Orin NX 16 GB |
| Last recorded platform | Seeed JetPack 6.2, L4T 36.4.3, kernel `5.15.148-tegra` |
| Linux user / hostname | `super-alex` / `super` |
| Installed application | `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated` |
| Existing interpreter | `/home/super-alex/atlas/venvs/atlas-school-pilot/bin/python` |
| Service | **USER** service `atlas.service`, operated as `super-alex` |
| Visitor / staff pages | `http://JETSON_CURRENT_IP:8765/` / `http://JETSON_CURRENT_IP:8765/admin` |

On the Jetson, these are safe first diagnostics, not repair commands:

```bash
hostname -I
systemctl --user show atlas.service -p ActiveState -p SubState -p NRestarts -p ExecMainStatus
curl --fail --max-time 5 http://127.0.0.1:8765/health
```

On the Windows hotspot-host computer, the reported current visitor URL is
`http://192.168.137.193:8765/`; staff use `/admin`. Do not put `super-alex@` in
a browser URL. `super.local` works only when mDNS and peer traffic allow it.
The old home IP `10.0.0.238` is not the school address. Obtain the actual IP
locally before attempting remote access.

If the page is reachable locally on the Jetson but not through its LAN address,
prefer an authorized local SSH tunnel rather than opening firewalls or changing
the running bind address blindly. On the laptop:

```bash
ssh -N -L 127.0.0.1:8766:127.0.0.1:8765 super-alex@192.168.137.193
```

Keep that terminal open and visit `http://127.0.0.1:8766/` or `/admin`. Substitute
the actual current IP if different. The laptop must have a permitted network
path to the Jetson; an unrelated remote computer cannot reach this private IP
without a separately approved secure path. Never expose SSH/admin/camera ports
to the public internet. USB-C serial is an optional local recovery route, not
something required for the working hotspot setup.

Only after the operator approves an interruption, use the existing user service:

```bash
systemctl --user start atlas.service
systemctl --user restart atlas.service
systemctl --user stop atlas.service
```

Choose ONE intended command. Do not run all three as a checklist, use `sudo`
to operate a different system service, launch another Uvicorn/device loop, kill
unknown processes or rename the installation. A restart interrupts the visit.
Avoid `systemctl status`/raw journal dumps in shared output: they can include
private application text. Prefer the selected `show` properties above.

## 4. Safe demo and filming checklist

1. Confirm the on-site operator is ready. No deployment/reboot during recording.
2. Keep the SG90 disconnected and all pan confirmations false.
3. Connect/charge the OpenComm headset and confirm the intended microphone and
   output in the authenticated staff UI. A flat headset is not a software bug.
4. Open the CURRENT IP, refresh the visitor page after a release (`Ctrl+F5` on
   Windows), select language and profile, and finish onboarding once.
5. Camera **degraded/offline is nonblocking** for camera-free conversations.
   Language pending means the visitor still needs to choose a language; do not
   bypass readiness or safety checks to remove a label.
6. Start one visit. Hear one introduction before the microphone opens. A wake
   address by itself should then wait silently for the question, not start a
   second introduction or preference interview.
7. Hear one short answer and one follow-up in the intended language. Test
   stopping during speech and starting a new visit; old speech must not return.
8. Use named-artwork questions or staff manual artwork context if the primary
   camera is offline. Capture and visual identification still need fresh frames.
9. Check the name sounds like **Atlas**, not a spelled/split acronym. The
   Cartesia fix changes only its outgoing complete-token spelling, not the UI,
   selected model/voice/language/speed. Audible confirmation was not received
   before this handoff; do not claim it has passed.

Camera-free does NOT mean internet-free. Deepgram, Cartesia and Gemini normally
need provider connectivity. Local fallbacks depend on installed assets and may
sound different for an entire answer; an already audible answer must never
switch voice halfway through. Cloud account/billing or campus filtering can
fail even when a phone or browser has internet. Do not change the voice/model
or weaken fallback/privacy rules speculatively.

## 5. Hardware boundaries — especially the unfinished servo

There are two separate cameras:

- Primary wearable XIAO ESP32-S3 camera: used for artwork YOLO/manual capture;
  owner reported an offline/damaged BAT+ contact on October 25. Repair/battery
  work is a separate approved physical task, not a dashboard fix.
- Arducam IMX477 CSI camera: independent staff preview/pan experiment. Its
  preview was observed live earlier on October 25, but current fresh frames,
  cabling and operation under motor load were NOT accepted at this handoff.

Before any future motor work, read [CAMERA_PAN](../atlas/docs/CAMERA_PAN.md),
get a NEW bounded-test approval from the present operator, and confirm fresh
wiring photos, bare horn clearance, correct supply and a physical disconnect.
The old one-shot approvals are not reusable during this two-week handoff.

- Normal `camera_pan.enabled`, `calibration_confirmed`, `pinmux_confirmed` and
  `power_confirmed` remain **false**. Do not set them just because code exists.
- Historical experimental wiring was SG90 red → 40-pin header physical 2 (5 V), brown →
  physical 6 (ground), orange → physical 32 (PWM7). This is a record, NOT an
  instruction to reconnect it. Original three-socket plugs must not be pushed
  onto arbitrary adjacent pins. Re-audit actual wiring after transport.
- Idle servo-side red/brown measured +5.1 V, and the orange extension passed
  continuity. Neither proves peak-current capacity, good operation under load,
  or a valid signal. Individually taped solder splices still need strain safety.
- The **19 V Jetson adapter must never directly power a 5 V SG90**. Do not use
  a GPIO signal as motor power, back-feed 5 V rails or inject 5 V into signals.
- Shut down normally and unplug barrel power and possible USB/HDMI back-power
  before changing wiring, probing continuity or handling the underside. Do not
  work on a powered loose board or remove its heatsink for ordinary diagnosis.
- Installed direct-PWM driver hash at last verification:
  `864644b304094284b5d1a20cbc8a2fef503dedf0b7a1595240b96836c3629d46`.
  It discovers controller identity, not unstable `pwmchipN` numbering; refuses
  already exported output; uses ownership locking and bounded cleanup. Do not
  weaken those guards or make ATLAS root to bypass existing permissions.
- Pin 32 is `32e0000.pwm`; the alternate supported route is physical 15 /
  `3280000.pwm`. Do not use the cooling-fan controller, an old Nano pin mapping
  or physical 33 without a separate carrier-specific review.
- Read-only pad value `0x00000400` at `0x02434080` is consistent with GP/SFIO
  output and no pull. The difference from reference `0x404` is a pull-down, NOT
  proof of a missing PWM enable. No raw register/clock write was approved.
- The available TACKLIFE CM03 is AUTO-only. Its behavior/test current at an
  inactive GPIO was not verified. Do not use it as a waveform tester or keep
  trying AUTO continuity on a powered signal.
- Direct header loopback is not a reliable workaround: the TXB0108 level
  shifters cannot reliably drive another TXB input. No strong pull-up/battery
  bias trick or software GPIO bit-banging is an approved repair.
- Actual signal waveform/levels, loaded power, servo operation, mounting/travel
  and cable slack are still unverified. No automatic sweep, camera mounting or
  unattended motion has been accepted. Software/readback is not a scope trace.

For motion, a network-disconnected dashboard is not a physical stop: an already
requested sweep/target can continue. Jog leases expire, but do not rely on a
browser close or Wi-Fi loss for safety. Use the emergency stop; clearing it
must not restart motion. For uncontrolled motion, heat, buzzing or a power
fault, the operator's immediate physical power disconnect takes precedence.
Do not enable EV3, tracking or unrelated motors as part of this handoff.

## 6. Networking evidence and current workaround

October 26 checks found the RTL8822CE adapter enabled/detected but disconnected;
scans initially returned no APs. A close phone hotspot appeared at reported
signal 2/100, while the adjacent laptop showed full bars. The owner reports
good home-Wi-Fi performance. This is NOT a confirmed broken card, antenna
fault, wrong-country configuration or school-authentication diagnosis.

The laptop also saw a WPA2-Personal school AP at 80% on 5 GHz channel 40. The
Jetson's `country 00`, self-managed rules included that frequency range with
passive scanning. Do not invent a regulatory/country or driver-install fix.
A proposed direct passive scan was not reported back before the operator
switched to the working Windows hotspot arrangement.

Keep that known-working arrangement for the demo unless the operator asks to
change it. Mobile hotspot sharing can stop when the Windows laptop sleeps or
its upstream connection changes. Direct school discovery/authentication and
campus client isolation remain unresolved. Existing enterprise/PEAP examples
in the [school guide](../atlas/docs/SCHOOL_WIFI_SETUP.md) are historical,
unverified assumptions, NOT the confirmed type of every school network.
Never disable server certificate checks or delete working profiles to test it.

For diagnosis, type EACH complete line on the Jetson, including `nmcli`:

```bash
nmcli radio wifi
nmcli device status
nmcli device wifi list --rescan yes
iw reg get
```

These do not print saved passwords. Do not use `--show-secrets`, dump
NetworkManager keyfiles, change country/power policy, restart networking or
switch the only SSH link without a local-console recovery plan and approval.

## 7. Private handover — GitHub is not a full device backup

The owner and teammate must arrange protected access separately. An agent must
never read/print/edit/commit live `.env`, credentials, private-key contents,
visitor logs/databases/transcripts, recordings, or raw camera media.

The human should privately confirm access to: GitHub write permission; Jetson
login/approved SSH authentication; the existing admin token; provider accounts
and billing; permitted Wi-Fi credentials; private camera headers/binaries; and
existing offline model/voice assets and recovery backups. Do not copy one
person's private SSH key into Git or an LLM conversation. Issue a teammate key
through an explicitly approved secure process if needed, not during a demo.

"Safety codes" that are actual passwords/tokens belong in protected human
storage, not this document. Documented emergency-stop behavior is public;
the admin token used to unlock/clear protected actions is not. Do not replace
auth with an easy public code. See [private-state policy](SECRETS_AND_PRIVATE_STATE.md).

Original workspace artifacts outside Git included deployment packages,
pre-PWM boot-file backups and branch-recovery bundles. Ask the owner to transfer
needed non-secret recovery artifacts privately. Git alone cannot reconstruct
ignored private headers, credentials, caches or a device-specific engine.
Do not flash/rebuild a working Jetson merely because those artifacts are absent
from a fresh laptop clone.

## 8. Priorities for the two weeks

1. Preserve a repeatable camera-free, headset-based demonstration using the
   working network. Verify navigation and pronunciation physically; record
   pass/fail without retaining visitor audio or names.
2. Fix only a reproduced problem, in the smallest owned module; keep mock mode
   and all privacy/cancellation/safety regressions intact. Do not start unrelated
   redesigns, model exports or dependency upgrades.
3. Keep direct school Wi-Fi, cloud availability and primary-camera repair as
   separate investigations. Ask school IT for approved network/certificate/
   peer-traffic information rather than guessing or weakening security.
4. Mechanical work stays paused until the operator explicitly resumes a scoped
   supervised task with suitable equipment. Never promise a working pan from
   a passed software test.
5. Before a code release follow [validation](VALIDATION_CHECKLIST.md) and
   [deployment/rollback](DEPLOYMENT_RUNBOOK.md). Keep the rollback backup until
   physical acceptance, not just HTTP 200.

## 9. Coordination and end-of-session record

If two Codex chats share a checkout, establish file ownership and inspect dirty
files before staging. They are not isolated just because the chat titles differ.
Only ONE chat/operator may own a Jetson deployment/test window at a time.
Before service/network changes, reboot, camera/PWM tests or deployment: state
the scope, get human approval, obtain an explicit timing ACK from active peers,
then report the result and release the window. Never infer a timeout is consent.
Original desktop thread IDs are not portable to the teammate's Codex account.
If an old chat is unavailable, ask the present human to resolve coordination;
do not wait for the absent owner or pretend another agent acknowledged.

End each work session with: branch + committed SHA; exact owned changes; tests
and their limitations; whether anything was pushed/deployed; installed revision
and backup path if changed; current IP/last verification date; unresolved risks;
and the next concrete action. Update [CURRENT_STATE](CURRENT_STATE.md) without
rewriting old dated evidence as if it happened today.

## 10. Handoff verification — October 26

This handoff updates documentation, repository instructions, the public
navigation/recovery required-file lists, and two regression checks. No runtime
implementation, device settings, service, packages, network or hardware output
was changed for this task.

- Focused repository/test-isolation gate: **25 passed**.
- Full guarded laptop suite: **3,791 passed, two skipped**, covering all 55
  test files exactly once in four disjoint partitions (14/14/14/13 files).
  Partition pass counts: 425 / 320 / 2,782 / 264. Each used a fresh Windows
  TEMP/TMP and pytest base directory, with live dotenv loading blocked before
  collection. Existing non-failing dependency/test-fixture warnings remain.
- Maintained Ruff, dependency consistency, compile, obvious-secret scan,
  recovery bundle, repository navigation and whitespace gates passed.
- All 24 changed Markdown files' local links resolved to tracked files.
- Synthetic admin JavaScript: **106 checks passed**. Headless visitor QA:
  **42 keyboard transitions**, 1024×768, reduced motion, delayed API responses,
  one pending progress save maximum, zero browser errors. No live server,
  cloud service or Jetson was contacted for these browser checks.
- The four historical unpublished commits were checked for protected filenames
  and obvious credential patterns before preservation. That branch is not a
  tested release candidate for deployment.

These results do not supply a fresh audible, camera, network, servo, thermal,
or iPad acceptance. Keep the private human-access checklist outstanding until
the teammate confirms it; no actual credentials were added to the handoff.
