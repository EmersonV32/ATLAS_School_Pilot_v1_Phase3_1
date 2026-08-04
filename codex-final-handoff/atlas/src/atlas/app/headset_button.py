"""Read multi-click actions from the Shokz USB consumer-control interface."""

from __future__ import annotations

import logging
import os
import re
import select
import struct
import threading
import time
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

EV_KEY = 1
KEY_PLAYPAUSE = 164
_INPUT_EVENT = struct.Struct("@llHHI")


def find_consumer_control_device(
    name_fragment: str = "Shokz",
    devices_file: str | Path = "/proc/bus/input/devices",
) -> str | None:
    """Return the evdev node for a matching Consumer Control interface."""
    try:
        text = Path(devices_file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    wanted = name_fragment.casefold()
    for block in text.split("\n\n"):
        folded = block.casefold()
        if wanted not in folded or "consumer control" not in folded:
            continue
        match = re.search(r"\b(event\d+)\b", block)
        if match:
            return f"/dev/input/{match.group(1)}"
    return None


def decode_input_events(data: bytes) -> list[tuple[int, int, int]]:
    """Decode complete Linux input_event records as (type, code, value)."""
    events: list[tuple[int, int, int]] = []
    for offset in range(0, len(data) - _INPUT_EVENT.size + 1, _INPUT_EVENT.size):
        _sec, _usec, event_type, code, value = _INPUT_EVENT.unpack_from(data, offset)
        events.append((event_type, code, value))
    return events


class ClickAccumulator:
    """Group button presses that arrive inside one multi-click window."""

    def __init__(self, window_s: float) -> None:
        self.window_s = window_s
        self.count = 0
        self.last_press_at = 0.0

    def press(self, now: float) -> int | None:
        completed = self.flush(now)
        self.count = min(3, self.count + 1)
        self.last_press_at = now
        return completed

    def flush(self, now: float) -> int | None:
        if not self.count or now - self.last_press_at < self.window_s:
            return None
        completed = self.count
        self.count = 0
        self.last_press_at = 0.0
        return completed


class HeadsetButtonListener:
    """Convert Shokz play/pause presses into one-, two-, or three-click actions."""

    def __init__(
        self,
        on_clicks: Callable[[int], None],
        *,
        device_path: str = "",
        device_name: str = "Shokz",
        key_code: int = KEY_PLAYPAUSE,
        click_window_s: float = 0.55,
    ) -> None:
        self._on_clicks = on_clicks
        self._configured_path = device_path
        self._device_name = device_name
        self._key_code = key_code
        self._click_window_s = click_window_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.device_path: str | None = None

    def start(self) -> str:
        path = self._configured_path or find_consumer_control_device(
            self._device_name
        )
        if not path:
            return "unavailable: Shokz Consumer Control input not found"
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        except OSError as exc:
            return f"unavailable: {exc}"
        os.close(fd)
        self.device_path = path
        self._thread = threading.Thread(
            target=self._run,
            name="atlas-headset-button",
            daemon=True,
        )
        self._thread.start()
        return f"ready on {path} (key {self._key_code})"

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._click_window_s + 1.0)

    def _run(self) -> None:
        if self.device_path is None:
            return
        clicks = ClickAccumulator(self._click_window_s)
        try:
            fd = os.open(self.device_path, os.O_RDONLY | os.O_NONBLOCK)
        except OSError as exc:
            logger.warning("[Button] Could not open %s: %s", self.device_path, exc)
            return
        try:
            while not self._stop.is_set():
                readable, _, _ = select.select([fd], [], [], 0.1)
                now = time.monotonic()
                if readable:
                    try:
                        data = os.read(fd, _INPUT_EVENT.size * 32)
                    except BlockingIOError:
                        data = b""
                    for event_type, code, value in decode_input_events(data):
                        if event_type == EV_KEY and code == self._key_code and value == 1:
                            completed = clicks.press(now)
                            if completed is not None:
                                self._dispatch(completed)
                completed = clicks.flush(now)
                if completed is not None:
                    self._dispatch(completed)
        except OSError as exc:
            logger.warning("[Button] Input listener stopped: %s", exc)
        finally:
            os.close(fd)

    def _dispatch(self, clicks: int) -> None:
        logger.info("[Button] Multifunction press count: %d", clicks)
        try:
            self._on_clicks(clicks)
        except Exception:
            logger.exception("[Button] Action callback failed")
