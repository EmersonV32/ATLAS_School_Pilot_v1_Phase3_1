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

`app_httpd.cpp`, `camera_index.h`, and `camera_pins.h` are based on Espressif's
Arduino ESP32 `CameraWebServer` example.
