"""Offline checks for camera health telemetry."""

from __future__ import annotations

import time

from atlas.vision.camera_source import (
    CameraSource,
    _MjpegCapture,
    build_gstreamer_jpeg_command,
    build_nvargus_pipeline,
)


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


def test_gstreamer_subprocess_replaces_opencv_sink_with_jpeg_pipe() -> None:
    pipeline = build_nvargus_pipeline(
        sensor_id=0,
        width=1920,
        height=1080,
        fps=30,
    )

    command = build_gstreamer_jpeg_command(pipeline)

    assert command[:2] == ["gst-launch-1.0", "-q"]
    assert "nvarguscamerasrc" in command
    assert "jpegenc" in command
    assert "fdsink" in command
    assert "appsink" not in command


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


def test_mjpeg_reader_extracts_one_complete_jpeg(monkeypatch) -> None:
    import cv2
    import numpy as np

    ok, jpeg = cv2.imencode(".jpg", np.zeros((12, 16, 3), dtype=np.uint8))
    assert ok

    class Response:
        def __init__(self) -> None:
            self.parts = iter((b"multipart header\r\n", jpeg.tobytes()))

        def read1(self, _size: int) -> bytes:
            return next(self.parts, b"")

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "atlas.vision.camera_source.urllib.request.urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    capture = _MjpegCapture("http://camera:81/stream")

    ready, frame = capture.read()

    assert ready is True
    assert frame.shape == (12, 16, 3)


def test_mjpeg_reader_rejects_endless_partial_frame(monkeypatch) -> None:
    class Response:
        def read1(self, _size: int) -> bytes:
            return b"partial jpeg bytes"

        def close(self) -> None:
            return None

    ticks = iter((10.0, 10.1, 12.1))
    monkeypatch.setattr(
        "atlas.vision.camera_source.urllib.request.urlopen",
        lambda *_args, **_kwargs: Response(),
    )
    monkeypatch.setattr(
        "atlas.vision.camera_source.time.monotonic",
        lambda: next(ticks),
    )
    capture = _MjpegCapture("http://camera:81/stream", timeout_s=2.0)

    try:
        capture.read()
    except TimeoutError as exc:
        assert "no complete frame" in str(exc)
    else:
        raise AssertionError("partial MJPEG stream did not time out")

    assert capture.isOpened() is False
