"""Offline checks for camera health telemetry."""

from __future__ import annotations

import time

from atlas.vision.camera_source import CameraSource, build_nvargus_pipeline


def test_nvargus_pipeline_uses_requested_sensor_and_low_latency_sink() -> None:
    pipeline = build_nvargus_pipeline(
        sensor_id=1,
        width=1920,
        height=1080,
        fps=30,
        flip_method=2,
    )

    assert pipeline.startswith("nvarguscamerasrc sensor-id=1")
    assert "width=(int)1920" in pipeline
    assert "height=(int)1080" in pipeline
    assert "framerate=(fraction)30/1" in pipeline
    assert "nvvidconv flip-method=2" in pipeline
    assert pipeline.endswith("appsink drop=true max-buffers=1 sync=false")


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
    source = CameraSource(0, reconnect_s=0.0, name="arducam")

    assert source.reconnect_s == 0.1
    assert source.name == "arducam"


def test_camera_status_marks_stalled_network_frame_unready() -> None:
    source = CameraSource("http://atlas-camera.local:81/stream")
    with source._lock:
        source._last_frame_at = time.monotonic() - 5.0
        source._ready.set()

    status = source.status()

    assert status["ready"] is False
    assert status["last_frame_age_s"] is not None
