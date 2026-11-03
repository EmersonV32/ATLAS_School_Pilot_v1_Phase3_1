"""A visit-scoped STT socket; idle periods transmit no microphone audio."""

from __future__ import annotations

import copy
import json
import math
import queue
import threading
from collections.abc import Callable
from typing import Any


class ReusableDeepgramConnection:
    def __init__(
        self, connection, receiver: Callable, *, sample_rate: int, channels: int,
        keepalive_s: float = 3.0,
    ) -> None:
        self.connection = connection
        self.messages: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=128)
        self._receiver = receiver
        self._bytes_per_second = sample_rate * channels * 2
        self._seed_bytes = max(1, sample_rate // 100) * channels * 2
        self._sent_bytes = 0
        self._send_lock = threading.Lock()
        self._stop = threading.Event()
        self._ended = threading.Event()
        self._keepalive_s = keepalive_s
        self.thread = threading.Thread(target=self._receive, daemon=True)
        self._keeper = threading.Thread(target=self._keepalive, daemon=True)

    @property
    def audio_seconds(self) -> float:
        return self._sent_bytes / self._bytes_per_second

    @property
    def usable(self) -> bool:
        return not self._stop.is_set() and not self._ended.is_set()

    def start(self) -> None:
        try:
            self.thread.start()
            # Start the audio protocol without capturing or uploading a visitor.
            # Provider timestamps include this generated silence.
            self.send(b"\0" * self._seed_bytes)
            self._keeper.start()
        except Exception:
            self.close()
            raise

    def _receive(self) -> None:
        try:
            self._receiver(self.connection, self.messages)
        finally:
            self._ended.set()
            self._stop.set()

    def send(self, payload: bytes | str) -> None:
        with self._send_lock:
            if not self.usable:
                raise OSError("STT connection is no longer available")
            self.connection.send(payload)
            if isinstance(payload, bytes):
                self._sent_bytes += len(payload)

    def _keepalive(self) -> None:
        while not self._stop.wait(self._keepalive_s):
            try:
                self.send(json.dumps({"type": "KeepAlive"}))
            except Exception:
                self._stop.set()
                try:
                    self.messages.put_nowait({"type": "_error"})
                except queue.Full:
                    pass
                return

    def close(self) -> None:
        self._stop.set()
        # Empty the bounded mailbox so a receiver cannot remain blocked on put.
        while True:
            try:
                self.messages.get_nowait()
            except queue.Empty:
                break
        try:
            self.connection.close()
        except Exception:
            pass
        for thread in (self.thread, self._keeper):
            if thread.is_alive() and thread is not threading.current_thread():
                thread.join(timeout=0.5)


def payload_for_turn(payload: dict[str, Any], offset: float) -> dict[str, Any] | None:
    """Convert cumulative provider timestamps and exclude previous-turn words."""
    if payload.get("type") != "Results":
        return payload
    try:
        start = float(payload["start"])
        end = start + float(payload["duration"])
    except (KeyError, ValueError, TypeError):
        return None  # An untimed result cannot establish its visit-turn boundary.
    if not math.isfinite(start) or not math.isfinite(end) or end < start:
        return None
    if end <= offset + 1e-6:
        return None
    result = copy.deepcopy(payload)
    if start < offset - 1e-6:
        alternatives = result.get("channel", {}).get("alternatives", [])
        for alternative in alternatives:
            words = alternative.get("words") or []
            current = []
            for word in words:
                try:
                    if float(word["start"]) >= offset - 1e-6:
                        current.append(word)
                except (KeyError, ValueError, TypeError):
                    continue
            if alternative.get("transcript") and not current:
                return None
            alternative["words"] = current
            alternative["transcript"] = " ".join(
                str(word.get("punctuated_word") or word.get("word", ""))
                for word in current
            ).strip()
    result["start"] = max(0.0, start - offset)
    result["duration"] = end - offset - result["start"]
    for alternative in result.get("channel", {}).get("alternatives", []):
        for word in alternative.get("words") or []:
            for key in ("start", "end"):
                if key in word:
                    word[key] = max(0.0, float(word[key]) - offset)
    return result
