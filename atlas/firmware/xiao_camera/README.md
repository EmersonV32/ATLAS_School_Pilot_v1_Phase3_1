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

The default balanced profile is 800x600 SVGA JPEG at quality 10 and a maximum
of 15 streamed frames per second. The stream sends only fresh frames, disables
browser caching, and enables Wi-Fi power saving whenever no stream client is
connected. This raises artwork detail above the former 640x480 profile while
limiting unnecessary radio traffic and idle heat.

After flashing, leave the camera streaming for 20 minutes and record the
observed FPS and enclosure temperature from the admin dashboard before sealing
the camera into a wearable case.

`app_httpd.cpp`, `camera_index.h`, and `camera_pins.h` are based on Espressif's
Arduino ESP32 `CameraWebServer` example.
