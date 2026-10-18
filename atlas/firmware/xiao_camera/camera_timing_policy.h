#pragma once

#include <stdint.h>

// All camera deadlines are far below half the uint32_t millis() range. An
// elapsed value >= half-range means a newer timestamp, not a multi-week stall.
// This also permits a genuine millis() wrap (about every 49.7 days).
constexpr bool cameraIntervalElapsed(uint32_t nowMs, uint32_t thenMs,
                                     uint32_t intervalMs) {
  const uint32_t elapsed = static_cast<uint32_t>(nowMs - thenMs);
  return elapsed < UINT32_C(0x80000000) && elapsed >= intervalMs;
}

constexpr bool cameraStreamStalledPolicy(bool active, uint32_t nowMs,
                                         uint32_t lastFrameMs, uint32_t timeoutMs) {
  return active && cameraIntervalElapsed(nowMs, lastFrameMs, timeoutMs);
}
