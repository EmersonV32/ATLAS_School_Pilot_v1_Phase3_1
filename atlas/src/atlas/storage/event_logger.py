"""Privacy-safe structured logging.

Emits one JSON object per line to a per-day log file. Hard guarantees:
  - never writes raw audio or raw images (they never reach this layer)
  - never writes student names (the system never collects them)
  - never writes API keys
  - transcripts are written ONLY when explicitly enabled in settings

The logger accepts a TelemetryEvent (validated) or keyword fields and
defends against accidental leakage by dropping unknown sensitive keys.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from atlas.config.settings import LoggingSettings
from atlas.models.telemetry import TelemetryEvent
from atlas.utils.ids import new_event_id
from atlas.utils.time import now_iso

# Keys we refuse to ever serialize, even if passed in `extra`.
_BLOCKED_KEYS = {
    "audio",
    "raw_audio",
    "image",
    "raw_image",
    "frame",
    "name",
    "student_name",
    "api_key",
    "gemini_api_key",
    "secret",
    "password",
}


class EventLogger:
    """Append-only JSON-lines logger with privacy guarantees."""

    def __init__(self, logs_dir: str | Path, settings: LoggingSettings) -> None:
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.settings = settings

    def _log_path(self) -> Path:
        day = now_iso()[:10]
        return self.logs_dir / f"atlas-{day}.jsonl"

    def _sanitize_extra(self, extra: dict[str, Any]) -> dict[str, str]:
        clean: dict[str, str] = {}
        for key, value in extra.items():
            if key.lower() in _BLOCKED_KEYS:
                continue
            clean[key] = str(value)
        return clean

    def log_event(self, event: TelemetryEvent) -> None:
        """Write a validated TelemetryEvent, applying privacy rules."""
        record = event.model_dump(exclude_none=True)

        # Enforce transcript privacy regardless of what was passed in.
        if not self.settings.log_transcripts:
            record.pop("transcript", None)

        if "extra" in record and isinstance(record["extra"], dict):
            record["extra"] = self._sanitize_extra(record["extra"])

        line = json.dumps(record, ensure_ascii=False)
        with self._log_path().open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def log(
        self,
        *,
        session_id: str,
        state: str,
        event: str = "",
        **fields: Any,
    ) -> TelemetryEvent:
        """Convenience constructor + write. Returns the written event."""
        # Drop any blocked keys before they reach the model.
        safe_fields = {
            k: v for k, v in fields.items() if k.lower() not in _BLOCKED_KEYS
        }
        telemetry = TelemetryEvent(
            event_id=new_event_id(),
            session_id=session_id,
            timestamp=now_iso(),
            state=state,
            event=event,
            **safe_fields,
        )
        self.log_event(telemetry)
        return telemetry

    def read_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent log records from today's file (for the API)."""
        path = self._log_path()
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()
        recent = lines[-limit:]
        out: list[dict[str, Any]] = []
        for line in recent:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
