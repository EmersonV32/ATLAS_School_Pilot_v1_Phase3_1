# Offline school Wi-Fi preparation — 2026-10-05

## October 26 operating update

The teammate reports successful Jetson connectivity through a Windows laptop
mobile hotspot sharing school Wi-Fi; the reported Jetson address was
`192.168.137.193` (DHCP, recheck locally). Direct school Wi-Fi discovery is
unresolved. Home Wi-Fi previously worked; no hardware fault is established.
See the [current handoff](../../handoff/2026-10-26_TEAMMATE_HANDOFF.md) for the
observations and browser/SSH access. Preserve the working connection.

The Enterprise/PEAP candidate below is an **older unconfirmed assumption**,
not instructions to replace the working profile or disable certificate
verification. A later Windows scan showed a school AP using WPA2-Personal on
5 GHz channel 40; that does not establish every school network's settings.
Obtain the intended SSID/security/certificate policy from school IT. Do not
change drivers, regulatory settings, or networking over the only remote link.

## Historical October 5 candidate

Assumption requested by the user: SSID `CBourget`, username/password entered
directly in Wi-Fi settings. Implemented candidate: WPA2-Enterprise PEAP with
MSCHAPv2. This is **not confirmation** of Bourget's actual EAP method. A browser
portal, different EAP method, 5 GHz-only network, device registration requirement,
or client isolation can make this candidate unusable. No live configuration or
firmware was changed by preparing these helpers.

## Security and secrets

Not requiring a *client* certificate is normal for PEAP. Not verifying the
*server* certificate allows a fake AP to capture authentication exchanges and
attack credentials. Verified mode requires `--ca-cert /absolute/public-ca.crt`
and `--server-name actual.authentication.server`; obtain both from IT. The
camera also needs an accurate clock for certificate validity checking.

For the specifically requested no-CA trial, `--allow-unverified-server` requires
typing `I ACCEPT THE RISK` locally. It is never silently selected. Prefer an
IT-approved isolated project/IoT network rather than exposing accounts or the
current unauthenticated camera stream to a shared campus network. Do not expose
camera ports publicly or use port forwarding to work around network isolation.

Credentials are prompted with hidden input, never command-line arguments.
Do not paste them into chat or commit/share headers, keyfiles, generated binaries,
logs, or archives. Git ignore is not encryption: OneDrive can still sync a local
camera header/build. Keep the machine/account and its sync access private.
The helper refuses to overwrite an existing school profile/header. It does not
read any existing credentials. The original hotspot header stays untouched.

## Camera: run locally on Windows, then flash explicitly

From the maintained `atlas` directory, using the existing Python environment:

```powershell
.\.venv\Scripts\python.exe .\scripts\configure_school_wifi.py --target camera --allow-unverified-server
```

After acknowledging the risk, enter the full username and password locally.
This creates `firmware/xiao_camera/wifi_school_secrets.h`; it does not flash.
The masked password in chat is not used. Existing hotspot settings are preserved.

For verified mode instead, omit the risk option and supply the public CA path
and exact server name. School support defaults to disabled without a configured
optional header. The camera scans for the school WPA2-Enterprise SSID at boot,
tries it if visible for up to 30 seconds of authentication, then falls back to
the original hotspot on failure (the scan adds some time before this deadline).
It does not leave a working hotspot connection solely to look for school.
On connection loss it first tries to recover the current network; if that fails
for 30 seconds, it reboots and repeats school-first selection. Failure to join
both networks also causes a reboot/retry, not permanent abandonment.

When ready to explicitly upload, close serial monitors and use the existing
`firmware/xiao_camera/build_and_flash.ps1 -Port COM3`, substituting the real port.
The known stream-watchdog race is a separate, still-unpatched issue; adding school
support does not establish stable live video.

## Jetson: save offline, do not switch the current link

Transfer only `scripts/configure_school_wifi.py` to the Jetson, not any private
camera header or generated firmware binary. Run this locally in a Jetson terminal:

```bash
sudo python3 scripts/configure_school_wifi.py --target jetson --allow-unverified-server
```

This stores a new root-only (0600) NetworkManager keyfile and loads the profile
named `ATLAS-school` with **autoconnect OFF**. It does not activate any connection,
restart NetworkManager, change existing profiles, or install system packages.
The password is stored in that protected system file, not a shell argument.
The saved school profile has priority 100, one automatic activation attempt,
and bounded authentication retries. The current link remains untouched while
the profile is staged offline.

### Enable school-first / hotspot-second on the Jetson

After entering credentials, use a **local Jetson console**, not an SSH-only
session. This step changes automatic connection policy; if disconnected,
NetworkManager can start connecting immediately. It may be done before school,
but cannot establish whether the school's authentication actually works.
List connection metadata only (no secrets):

```bash
nmcli -f NAME,UUID,TYPE connection show
```

Identify the existing phone hotspot's Wi-Fi profile UUID. Substitute that UUID
below, not the hotspot password. Do not select an Ethernet or unrelated profile:

```bash
sudo nmcli connection modify uuid "HOTSPOT_PROFILE_UUID" connection.autoconnect yes connection.autoconnect-priority 50
sudo nmcli connection modify id ATLAS-school connection.autoconnect-priority 100 connection.autoconnect-retries 1 connection.auth-retries 2 connection.autoconnect yes
nmcli -f DEVICE,TYPE,STATE,CONNECTION device status
```

These commands preserve both profiles' credentials and do not explicitly bring
any connection up/down or restart NetworkManager. School wins over hotspot when
both are eligible on the same idle Wi-Fi adapter. A failed school activation is
blocked temporarily, allowing the hotspot candidate to be tried. School is not
retried forever before fallback; NetworkManager may reconsider it after its
retry cooldown if still disconnected. Its authentication/DHCP timers differ
from the camera's 30-second window.

Neither device preempts a working hotspot when school appears later. At school,
boot both with the hotspot enabled so they select from the same visible networks.
Other saved Wi-Fi profiles can also participate; inspect their autoconnect
priorities if they compete with these two. Each device authenticates independently,
so one could join school while the other falls back. Automatic network choice
does not synchronize them or detect school client isolation. If they end up on
different networks, use the local Jetson console to select the shared reachable
network after checking the camera's status; do not cycle a remote-only link.

For a deliberate on-site school authentication test, `nmcli connection up
ATLAS-school` is a manual activation and can disconnect SSH. Use local access.
The Jetson, camera, and operator laptop need mutually reachable network paths;
their home/hotspot addresses will not identify them on the school network.

To disable just the school candidate again without deleting either profile:

```bash
sudo nmcli connection modify id ATLAS-school connection.autoconnect no
```

This does not disconnect an already active school connection. Priority/fallback
semantics follow NetworkManager's documented connection properties:
https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/settings-connection.html

## Acceptance still due at school

- Authentication succeeds with the actual school method and credentials.
- Camera and Jetson can communicate; school client isolation does not block it.
- Camera video is stable, not only its settings page or TCP ports.
- School absent/authentication failure retains the hotspot fallback.
- Jetson SSH/dashboard work at the new address without exposing ports externally.
- Certificate validation (if configured) and clock behavior are checked on target.

The offline gate comprises helper regression tests, real ESP32 core 3.3.11
compile/link checks with synthetic headers, the existing Python suite, and the
repository secret/recovery/diff checks. None establishes school connectivity.

Final local results (2026-10-05): 30 helper tests passed; full suite 3,033 passed,
1 skipped with one existing Starlette/httpx deprecation warning. All three
firmware variants compiled/linked with the policy assertions. Changed Python
files pass Ruff; the broader runtime/test scope retains 31 existing lint findings
in untouched files. Secret/recovery, dependency and diff checks pass. No actual
school credentials/profile were entered, and no physical device was updated.
