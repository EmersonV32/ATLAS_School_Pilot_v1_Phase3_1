#pragma once

#include "esp_camera.h"

// Balanced for artwork recognition: more detail than VGA without allowing
// an unbounded MJPEG stream to maximize radio load and enclosure heat.
constexpr framesize_t kAtlasFrameSize = FRAMESIZE_SVGA;
constexpr int kAtlasFrameWidth = 800;
constexpr int kAtlasFrameHeight = 600;
constexpr int kAtlasJpegQuality = 10;
constexpr int kAtlasTargetFps = 15;
constexpr char kAtlasTargetFpsHeader[] = "15";
constexpr int64_t kAtlasFrameIntervalUs = 1000000 / kAtlasTargetFps;
