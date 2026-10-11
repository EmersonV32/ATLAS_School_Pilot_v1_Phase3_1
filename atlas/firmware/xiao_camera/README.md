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
of 15 streamed frames per second. The stream sends only fresh frames, disables
browser caching, and enables Wi-Fi power saving whenever no stream client is
connected. Quality 14 retains the 800x600 artwork detail while avoiding the
motion-heavy frame stalls measured at quality 10. A five-second stream
watchdog restarts the camera automatically if a client connection wedges while
partial frame bytes are being transmitted.

After flashing, leave the camera streaming for 20 minutes and record the
observed FPS and enclosure temperature from the admin dashboard before sealing
the camera into a wearable case.

`app_httpd.cpp`, `camera_index.h`, and `camera_pins.h` are based on Espressif's
Arduino ESP32 `CameraWebServer` example.

## Optional school enterprise profile (prepared 2026-10-05)

School support assumes **WPA2-Enterprise PEAP/MSCHAPv2**, not a browser portal,
shared-password PSK, EAP-TLS, or a proven Bourget configuration. No school
authentication has been tested. See `../../docs/SCHOOL_WIFI_SETUP.md`.

`scripts/configure_school_wifi.py --target camera` is run locally by the
operator to create the ignored `wifi_school_secrets.h`. It never reads or
replaces the existing hotspot header. Without this optional header, the
previous hotspot behavior remains. At boot, a configured school profile is
tried only if its 2.4 GHz WPA2-Enterprise SSID is visible. If it fails, EAP is
disabled and the original hotspot is used. After a prolonged connection loss,
the existing reboot/reconnection path repeats this selection.

Verified-server mode needs the IT-supplied public CA and exact server name,
and an accurate device clock for certificate validity checks. Do not disable
certificate time checks as a connectivity workaround. Unverified-server mode
is OFF by default and requires both an explicit command option and a typed
local risk acknowledgement. It can expose the account to a fake school AP.

`scripts/verify_school_firmware.ps1` compiles hotspot-only, unverified-school,
and verified-school variants with synthetic values and compile-time policy
regressions. It never reads private headers or uploads firmware. Actual school
authentication, fallback behavior on hardware, peer connectivity, and sustained
streaming still require physical tests. The separately diagnosed stream-watchdog
timing issue is not changed by this school-network addition.
