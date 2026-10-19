# ATLAS XIAO Camera

Firmware for the Seeed Studio XIAO ESP32-S3 Sense wireless helmet camera.
It serves the current frame as a low-latency MJPEG stream for the Jetson.

## Endpoints

- Controls: `http://atlas-camera.local`
- MJPEG: `http://atlas-camera.local:81/stream`

## First-time setup

1. Connect the XIAO with a USB data cable.
2. Run `configure_wifi.ps1`; credentials are stored only in the ignored
   `wifi_secrets.h` file.
3. Enter bootloader mode by holding B while tapping R.
4. Run `build_and_flash.ps1 -Port COM3`.

The build uses the `XIAO_ESP32S3` board definition, OPI PSRAM, the 8 MB maximum
application partition, two PSRAM frame buffers, and latest-frame capture.

The default balanced profile is 800x600 SVGA JPEG at quality 14 and a maximum
of 15 streamed frames per second. The stream sends only fresh frames and disables
browser caching. The October 18 arrival build keeps Wi-Fi power saving OFF,
including while idle, to avoid radio-mode transitions during first-frame
transmission. This can increase idle battery consumption; battery/thermal
acceptance is still required. Quality 14 retains the 800x600 artwork detail.
HTTP send/receive waits are bounded to two seconds, below the five-second
stream-stall recovery deadline. A genuine stalled stream can still restart the
camera. These mitigations do not prove sustained streaming reliability: see
the dated onsite deployment record for actual hardware results.

After flashing, leave the camera streaming for 20 minutes and record the
observed FPS and enclosure temperature from the admin dashboard before sealing
the camera into a wearable case.

`app_httpd.cpp`, `camera_index.h`, and `camera_pins.h` are based on Espressif's
Arduino ESP32 `CameraWebServer` example.

## Optional primary personal network (prepared 2026-10-18)

For the current release, follow [the onsite runbook](../../docs/2026-10-18_ONSITE_DEPLOYMENT.md).
`build_and_flash.ps1 -BuildOnly` prepares an ignored private cached firmware
without contacting a device. `-UploadOnly -Port COM3` uploads only after checking
source/header/core/binary provenance; substitute the verified actual port.
Do not share the private cache, build manifests, diagnostics or firmware binaries.

`scripts/configure_personal_wifi.py` prepares the new SSID/password network
without replacing the old hotspot or enterprise headers. The optional ignored
`wifi_personal_secrets.h` uses `WIFI_PERSONAL_CONFIGURED`,
`WIFI_PERSONAL_WPA3_ONLY`, `WIFI_PERSONAL_SSID`, and `WIFI_PERSONAL_PASSWORD`.
The public example is disabled and contains no real credentials.

Boot preference is **new personal network, configured school enterprise,
optional home fallback, then original hotspot**. Each optional profile is tried only when a compatible
SSID is visible; each visible optional profile has a bounded 30-second attempt.
If the active connection is lost, normal reconnection is attempted for 30
seconds, then the existing reboot path repeats that preference. An already
working fallback is not interrupted just because a preferred AP appears later.
Two devices select independently: they must actually join the same reachable
LAN for the Jetson to read the camera. Hidden SSIDs are not supported by this
visible-network selection.

The XIAO ESP32-S3 radio is **2.4 GHz only**, not 5/6 GHz. Auto/WPA2 mode requires
at least WPA2 personal and also permits WPA3; WPA3-only mode requires SAE and
protected management frames. SAE hunting-and-pecking and hash-to-element are
enabled in the installed ESP32 3.3.11 core. Open/WEP/WPA1/enterprise APs are not
accepted by this personal profile. This does not bypass captive portals,
client isolation, or institutional access rules. Real AP authentication and
peer traffic must be tested onsite; a compile is not proof of WPA3 negotiation.

The 2026-10-18 firmware fixes the audited false-stall race: stream state is
snapshotted together under an ESP32 critical section, and a newer frame
timestamp cannot underflow into a false five-second timeout. Genuine stalls,
including `millis()` wrap, still trigger recovery. Wi-Fi reconnect intervals
are now wrap-safe and do not use zero as an uninitialized timestamp. These are
covered by deterministic C++ policy assertions compiled with the real sketch.
Hardware streaming and reconnect soak checks remain required after flashing.

### Optional home fallback

From `atlas/`, run `.venv/Scripts/python.exe scripts/configure_personal_wifi.py
--target camera-home` in a real local terminal. SSID and password prompts are
hidden. This creates only the ignored `wifi_home_secrets.h`, with the same
WPA2/WPA3 validation and encoding as the primary personal profile. It does not
replace the personal school network, enterprise network, original hotspot or
Jetson profiles. Repeat setup needs explicit `--replace` and retains a private
backup. Never print or share the header or its build artifacts.

Rebuild with `-BuildOnly`, then use verified `-UploadOnly` on the actual port.
Home selection is skipped when unconfigured, out of range or incompatible;
visible authentication has the same 30-second bound. The previous five firmware
variants and a sixth `home-with-personal-school` synthetic variant check that
adding home support does not require private headers or remove earlier profiles.

## Optional school enterprise profile (prepared 2026-10-05)

School support assumes **WPA2-Enterprise PEAP/MSCHAPv2**, not a browser portal,
shared-password PSK, EAP-TLS, or a proven Bourget configuration. No school
authentication has been tested. See `../../docs/SCHOOL_WIFI_SETUP.md`.

`scripts/configure_school_wifi.py --target camera` is run locally by the
operator to create the ignored `wifi_school_secrets.h`. It never reads or
replaces the existing hotspot header. Without this optional header, the
previous school/hotspot behavior remains. After the optional personal primary,
a configured school profile is
tried only if its 2.4 GHz WPA2-Enterprise SSID is visible. If it fails, EAP is
disabled and the optional home network, then original hotspot, are tried.
After a prolonged connection loss,
the existing reboot/reconnection path repeats this selection.

Verified-server mode needs the IT-supplied public CA and exact server name,
and an accurate device clock for certificate validity checks. Do not disable
certificate time checks as a connectivity workaround. Unverified-server mode
is OFF by default and requires both an explicit command option and a typed
local risk acknowledgement. It can expose the account to a fake school AP.

`scripts/verify_school_firmware.ps1` compiles hotspot-only, personal-auto,
personal-WPA3-with-school-fallback, unverified-school, and verified-school
variants with synthetic values and compile-time policy
regressions. It never reads private headers or uploads firmware. Actual school
authentication, fallback behavior on hardware, peer connectivity, and sustained
streaming still require physical tests. It never copies existing private headers.
