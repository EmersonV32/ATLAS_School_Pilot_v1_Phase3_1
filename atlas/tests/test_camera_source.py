"""Offline checks for camera health telemetry."""

from __future__ import annotations

import time

from atlas.vision.camera_source import CameraSource


def test_camera_status_reports_observed_fps_without_opening_hardware() -> None:
    source = CameraSource("http://atlas-camera.local:81/stream", fps=15)
    now = time.monotonic()
    with source._lock:
        source._frame_times.extend((now - 1.0, now - 0.5, now))
        source._frame_number = 3

    status = source.status()

    assert status["source"] == "http://atlas-camera.local:81/stream"
    assert status["observed_fps"] == 2.0
    assert status["requested_fps"] == 15
    assert status["reconnect_count"] == 0


def test_camera_reconnect_delay_has_a_safe_minimum() -> None:
    source = CameraSource(0, reconnect_s=0.0)

    assert source.reconnect_s == 0.1


def test_camera_status_marks_stalled_network_frame_unready() -> None:
    source = CameraSource("http://atlas-camera.local:81/stream")
    with source._lock:
        source._last_frame_at = time.monotonic() - 5.0
        source._ready.set()

    status = source.status()

    assert status["ready"] is False
    assert status["last_frame_age_s"] is not None
