"""Low-latency camera reader for USB cameras and MJPEG streams."""

from __future__ import annotations

import logging
import platform
import threading
import time
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

def normalize_camera_source(source: str | int) -> str | int:
    """Convert a numeric camera setting to an OpenCV device index."""
    if isinstance(source, int):
        return source
    value = str(source).strip()
    if value.isdigit():
        return int(value)
    return value


class CameraSource:
    """Continuously reads frames and exposes only the newest one.

    Network cameras can buffer seconds of old video when inference is slower
    than capture. A dedicated reader thread consumes that queue so callers
    always receive the freshest frame instead of processing stale frames.
    """

    def __init__(
        self,
        source: str | int,
        width: int = 1280,
        height: int = 720,
        fps: int = 15,
        rotation_degrees: int = 0,
        reconnect_s: float = 1.0,
    ) -> None:
        self.source = normalize_camera_source(source)
        self.width = width
        self.height = height
        self.fps = fps
        self.rotation_degrees = rotation_degrees % 360
        if self.rotation_degrees not in (0, 90, 180, 270):
            raise ValueError("camera_rotation_degrees must be 0, 90, 180, or 270")
        self.reconnect_s = max(0.1, reconnect_s)

        self._capture = None
        self._frame: Any = None
        self._frame_number = 0
        self._last_frame_at = 0.0
        self._last_error: str | None = None
        self._opened_at = 0.0
        self._reconnect_count = 0
        self._consecutive_failures = 0
        self._frame_times: deque[float] = deque(maxlen=60)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None

    def _open(self):
        import cv2  # type: ignore

        if isinstance(self.source, int) and platform.system() == "Linux":
            capture = cv2.VideoCapture(self.source, cv2.CAP_V4L2)
        else:
            # ESP32 MJPEG streams occasionally stop sending frames without
            # closing the HTTP connection. Ask FFmpeg to return from a stuck
            # read so this reader can perform its normal reconnect instead of
            # leaving the dashboard on a frozen image for about a minute.
            params: list[int] = []
            for attribute, timeout_ms in (
                ("CAP_PROP_OPEN_TIMEOUT_MSEC", 5000),
                ("CAP_PROP_READ_TIMEOUT_MSEC", 4000),
            ):
                property_id = getattr(cv2, attribute, None)
                if property_id is not None:
                    params.extend((property_id, timeout_ms))
            if params:
                try:
                    capture = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG, params)
                except (TypeError, cv2.error):
                    capture = cv2.VideoCapture(self.source)
            else:
                capture = cv2.VideoCapture(self.source)
            # Some OpenCV builds expose the timeout constants but do not
            # accept the three-argument constructor. Retain the previous
            # generic backend as a compatibility fallback.
            if not capture.isOpened():
                capture.release()
                capture = cv2.VideoCapture(self.source)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if isinstance(self.source, int):
            capture.set(
                cv2.CAP_PROP_FOURCC,
                cv2.VideoWriter_fourcc("M", "J", "P", "G"),
            )
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            capture.set(cv2.CAP_PROP_FPS, self.fps)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"could not open camera source {self.source!r}")
        logger.info(
            "Camera opened: %r [requested=%dx%d@%dfps]",
            self.source,
            self.width,
            self.height,
            self.fps,
        )
        return capture

    def start(self, timeout_s: float = 10.0) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._reader_loop,
            name="atlas-camera-reader",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=max(0.0, timeout_s)):
            detail = self._last_error or "no frame received"
            raise RuntimeError(f"camera did not become ready: {detail}")

    def _reader_loop(self) -> None:
        import cv2  # type: ignore

        rotate_codes = {
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE,
        }
        reconnect_delay = self.reconnect_s
        while not self._stop.is_set():
            if self._capture is None:
                try:
                    self._capture = self._open()
                    with self._lock:
                        if self._opened_at:
                            self._reconnect_count += 1
                            logger.info(
                                "Camera reconnected [count=%d]",
                                self._reconnect_count,
                            )
                        self._opened_at = time.monotonic()
                        self._last_error = None
                        self._consecutive_failures = 0
                    reconnect_delay = self.reconnect_s
                except Exception as exc:
                    with self._lock:
                        self._last_error = str(exc)
                    logger.warning("Camera open failed; retrying in %.1fs: %s", reconnect_delay, exc)
                    self._stop.wait(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 1.8, 10.0)
                    continue

            ok, frame = self._capture.read()
            if not ok:
                with self._lock:
                    self._consecutive_failures += 1
                    failures = self._consecutive_failures
                    self._last_error = "camera read failed"
                # One empty network frame should not tear down the stream. Three
                # failures means the reader owns a controlled reconnect instead.
                if failures < 3:
                    self._stop.wait(0.05)
                    continue
                logger.warning(
                    "Camera read failed %d times; reconnecting in %.1fs",
                    failures,
                    reconnect_delay,
                )
                with self._lock:
                    self._frame = None
                    self._ready.clear()
                self._capture.release()
                self._capture = None
                self._stop.wait(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.8, 10.0)
                continue

            if self.rotation_degrees:
                frame = cv2.rotate(frame, rotate_codes[self.rotation_degrees])
            with self._lock:
                self._frame = frame
                self._frame_number += 1
                self._last_frame_at = time.monotonic()
                self._frame_times.append(self._last_frame_at)
                self._consecutive_failures = 0
            self._ready.set()

        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def latest(self, copy: bool = False) -> tuple[Any, int]:
        """Return ``(frame, sequence_number)`` or ``(None, 0)``."""
        with self._lock:
            frame = self._frame
            number = self._frame_number
            if copy and frame is not None:
                frame = frame.copy()
            return frame, number

    def wait_for_new_frame(
        self, after_number: int = 0, timeout_s: float = 2.0
    ) -> tuple[Any, int]:
        deadline = time.monotonic() + timeout_s
        while not self._stop.is_set() and time.monotonic() < deadline:
            frame, number = self.latest()
            if frame is not None and number > after_number:
                return frame, number
            time.sleep(0.005)
        return None, after_number

    def status(self) -> dict[str, Any]:
        with self._lock:
            age = (
                time.monotonic() - self._last_frame_at if self._last_frame_at else None
            )
            observed_fps = 0.0
            if len(self._frame_times) > 1:
                elapsed = self._frame_times[-1] - self._frame_times[0]
                if elapsed > 0:
                    observed_fps = (len(self._frame_times) - 1) / elapsed
            # A reader thread can remain alive while a network stream is
            # silently stalled. Report that as unavailable, not "ready".
            fresh = age is not None and age <= 4.5
            return {
                "source": self.source,
                "ready": self._ready.is_set() and fresh,
                "frame_number": self._frame_number,
                "last_frame_age_s": age,
                "last_error": self._last_error,
                "observed_fps": round(observed_fps, 1),
                "requested_width": self.width,
                "requested_height": self.height,
                "requested_fps": self.fps,
                "reconnect_count": self._reconnect_count,
                "consecutive_failures": self._consecutive_failures,
            }

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def __enter__(self) -> CameraSource:
        self.start()
        return self

    def __exit__(self, *_exc) -> None:
        self.stop()
