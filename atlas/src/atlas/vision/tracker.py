"""ArtworkTracker: stabilises per-frame detections into a reliable state.

Wraps any BaseDetector and adds:
  - multi-frame stability (an artwork must be seen on N consecutive frames
    above the confidence threshold before it becomes "stable")
  - last-stable fallback (a low-confidence frame does not immediately lose
    the artwork the visitor is standing in front of)
  - manual override (the teacher dashboard can pin an artwork; vision is
    ignored until the override is cleared)
  - optional validation that detected artwork_ids exist in the loaded
    content pack (guards against YOLO label -> artwork_id mapping drift)

The tracker never raises on detector errors — a broken camera degrades to
"no artwork", never to a crash.
"""
from __future__ import annotations

import logging
import time
from dataclasses import replace
from typing import Any

from .detector import ArtworkDetection, BaseDetector

logger = logging.getLogger(__name__)


class ArtworkTracker:
    def __init__(
        self,
        detector: BaseDetector,
        conf_threshold: float = 0.65,
        stability_frames: int = 3,
        allow_last_stable: bool = True,
        valid_artwork_ids: set[str] | None = None,
    ) -> None:
        self._detector = detector
        self._conf_threshold = conf_threshold
        self._stability_frames = max(1, stability_frames)
        self._allow_last_stable = allow_last_stable
        # None disables validation (e.g. no pack loaded yet).
        self._valid_ids = valid_artwork_ids

        self._streak_id: str | None = None
        self._streak_count = 0
        self._last_stable: ArtworkDetection | None = None
        self._manual: ArtworkDetection | None = None

    # -- manual override -------------------------------------------------
    def set_manual_override(self, artwork_id: str, label: str | None = None) -> None:
        """Pin an artwork regardless of vision. Used by the dashboard."""
        self._manual = ArtworkDetection(
            artwork_id=artwork_id,
            label=label or artwork_id.replace("_", " ").title(),
            confidence=1.0,
            timestamp=time.time(),
            source="manual_override",
            stable=True,
        )
        logger.info("Manual artwork override set: %s", artwork_id)

    def clear_manual_override(self) -> None:
        self._manual = None
        logger.info("Manual artwork override cleared.")

    @property
    def manual_override(self) -> ArtworkDetection | None:
        return self._manual

    @property
    def last_stable(self) -> ArtworkDetection | None:
        return self._last_stable

    # -- per-frame update -------------------------------------------------
    def update(self, frame: Any = None) -> ArtworkDetection | None:
        """Process one frame and return the current artwork context.

        Returns a detection whose `source` explains where it came from,
        or None when there is genuinely no artwork context available.
        """
        if self._manual is not None:
            return self._manual

        detection: ArtworkDetection | None = None
        try:
            detection = self._detector.detect(frame)
        except Exception as exc:
            logger.warning("Detector error (treated as no detection): %s", exc)

        if detection is not None and self._valid_ids is not None:
            if detection.artwork_id not in self._valid_ids:
                logger.warning(
                    "Detected unknown artwork_id %r (label %r) — check the "
                    "YOLO label -> artwork_id mapping.",
                    detection.artwork_id,
                    detection.label,
                )
                detection = None

        if detection is not None and detection.confidence >= self._conf_threshold:
            if detection.artwork_id == self._streak_id:
                self._streak_count += 1
            else:
                self._streak_id = detection.artwork_id
                self._streak_count = 1
            stable = self._streak_count >= self._stability_frames
            tracked = replace(
                detection,
                timestamp=detection.timestamp or time.time(),
                source="vision",
                stable=stable,
            )
            if stable:
                self._last_stable = tracked
            return tracked

        # Low confidence or nothing detected: break the streak, fall back.
        self._streak_id = None
        self._streak_count = 0
        if self._allow_last_stable and self._last_stable is not None:
            return replace(self._last_stable, source="last_stable")
        return None

    def detect(self, frame: Any = None) -> ArtworkDetection | None:
        """BaseDetector-compatible alias so the tracker can drop in
        wherever a detector is expected (e.g. SessionRunner)."""
        return self.update(frame)

    # -- status ------------------------------------------------------------
    def status(self) -> dict:
        """Privacy-safe snapshot for the dashboard."""
        current = self._manual or self._last_stable
        return {
            "artwork_id": current.artwork_id if current else None,
            "label": current.label if current else None,
            "confidence": current.confidence if current else None,
            "stable": bool(current and current.stable),
            "source": current.source if current else "none",
            "manual_override": self._manual is not None,
        }
