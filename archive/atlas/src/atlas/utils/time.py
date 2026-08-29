"""Time helpers: ISO timestamps and a latency timer."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from types import TracebackType


def now_iso() -> str:
    """Current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def now_ms() -> float:
    """Monotonic clock reading in milliseconds (for latency math)."""
    return time.monotonic() * 1000.0


class Timer:
    """Context manager measuring elapsed wall time in milliseconds.

    Example:
        with Timer() as t:
            do_work()
        print(t.elapsed_ms)
    """

    def __init__(self) -> None:
        self._start: float = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = now_ms()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.elapsed_ms = now_ms() - self._start
