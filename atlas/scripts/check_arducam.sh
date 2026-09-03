#!/usr/bin/env bash
set -u

width="${ATLAS_ARDUCAM_WIDTH:-1920}"
height="${ATLAS_ARDUCAM_HEIGHT:-1080}"
fps="${ATLAS_ARDUCAM_FPS:-30}"
if (( $# > 0 )); then
  sensors=("$@")
else
  # JetPack 6 may expose a camera connected to CAM0 as sensor-id 1.
  sensors=(1 0)
fi

if ! command -v gst-launch-1.0 >/dev/null 2>&1; then
  echo "FAIL: gst-launch-1.0 is not installed."
  exit 1
fi
if ! gst-inspect-1.0 nvarguscamerasrc >/dev/null 2>&1; then
  echo "FAIL: NVIDIA nvarguscamerasrc is unavailable."
  exit 1
fi

echo "Jetson camera devices:"
if command -v v4l2-ctl >/dev/null 2>&1; then
  v4l2-ctl --list-devices || true
else
  echo "v4l2-ctl is not installed; continuing with Argus probes."
fi

for sensor_id in "${sensors[@]}"; do
  echo "Testing nvarguscamerasrc sensor-id=${sensor_id} at ${width}x${height}@${fps}..."
  if timeout 12s gst-launch-1.0 -q \
      nvarguscamerasrc sensor-id="${sensor_id}" num-buffers=10 ! \
      "video/x-raw(memory:NVMM),width=(int)${width},height=(int)${height},format=(string)NV12,framerate=(fraction)${fps}/1" ! \
      fakesink sync=false; then
    echo "PASS: sensor-id=${sensor_id} produced frames."
    echo "Set hardware.arducam_sensor_id to ${sensor_id}."
    exit 0
  fi
  echo "No frames from sensor-id=${sensor_id}."
done

echo "FAIL: no tested Argus sensor produced frames."
echo "Check the powered-off ribbon orientation, IMX477 driver/overlay, and carrier-board port mapping."
exit 2
