"""Low-latency camera reader for USB cameras and MJPEG streams."""

from __future__ import annotations

import logging
import platform
import threading
import time
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
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None

    def _open(self):
        import cv2  # type: ignore

        if isinstance(self.source, int) and platform.system() == "Linux":
            capture = cv2.VideoCapture(self.source, cv2.CAP_V4L2)
        else:
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
        logger.info("Camera opened: %r", self.source)
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
        while not self._stop.is_set():
            if self._capture is None:
                try:
                    self._capture = self._open()
                    self._last_error = None
                except Exception as exc:
                    self._last_error = str(exc)
                    logger.warning("Camera open failed: %s", exc)
                    self._stop.wait(self.reconnect_s)
                    continue

            ok, frame = self._capture.read()
            if not ok:
                self._last_error = "camera read failed"
                logger.warning("Camera read failed; reconnecting")
                self._capture.release()
                self._capture = None
                self._stop.wait(self.reconnect_s)
                continue

            if self.rotation_degrees:
                frame = cv2.rotate(frame, rotate_codes[self.rotation_degrees])
            with self._lock:
                self._frame = frame
                self._frame_number += 1
                self._last_frame_at = time.monotonic()
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
            return {
                "source": self.source,
                "ready": self._ready.is_set(),
                "frame_number": self._frame_number,
                "last_frame_age_s": age,
                "last_error": self._last_error,
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
