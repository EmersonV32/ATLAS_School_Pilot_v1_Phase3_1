"""Tests for the ArtworkTracker (stability, override, fallback)."""
from __future__ import annotations

from typing import Any

from atlas.vision.detector import ArtworkDetection, BaseDetector
from atlas.vision.tracker import ArtworkTracker


class ScriptedDetector(BaseDetector):
    """Returns a scripted sequence of detections (None = nothing seen)."""

    def __init__(self, script: list[ArtworkDetection | None]) -> None:
        self.script = list(script)
        self.i = 0

    def detect(self, frame: Any) -> ArtworkDetection | None:
        if self.i >= len(self.script):
            return None
        det = self.script[self.i]
        self.i += 1
        return det


def _det(artwork_id: str, conf: float = 0.9) -> ArtworkDetection:
    return ArtworkDetection(artwork_id=artwork_id, label=artwork_id, confidence=conf)


class TestStability:
    def test_needs_consecutive_frames_to_stabilise(self):
        tracker = ArtworkTracker(
            ScriptedDetector([_det("mona_lisa")] * 3), stability_frames=3
        )
        assert tracker.update().stable is False
        assert tracker.update().stable is False
        assert tracker.update().stable is True

    def test_artwork_change_resets_streak(self):
        tracker = ArtworkTracker(
            ScriptedDetector(
                [_det("mona_lisa"), _det("mona_lisa"), _det("starry_night")]
            ),
            stability_frames=3,
        )
        tracker.update()
        tracker.update()
        third = tracker.update()
        assert third.artwork_id == "starry_night"
        assert third.stable is False

    def test_low_confidence_falls_back_to_last_stable(self):
        tracker = ArtworkTracker(
            ScriptedDetector([_det("mona_lisa")] * 3 + [_det("mona_lisa", 0.2)]),
            stability_frames=3,
        )
        for _ in range(3):
            tracker.update()
        fallback = tracker.update()
        assert fallback is not None
        assert fallback.artwork_id == "mona_lisa"
        assert fallback.source == "last_stable"

    def test_no_detection_and_no_history_returns_none(self):
        tracker = ArtworkTracker(ScriptedDetector([None]))
        assert tracker.update() is None

    def test_last_stable_can_be_disabled(self):
        tracker = ArtworkTracker(
            ScriptedDetector([_det("mona_lisa")] * 3 + [None]),
            stability_frames=3,
            allow_last_stable=False,
        )
        for _ in range(3):
            tracker.update()
        assert tracker.update() is None

    def test_visualization_reports_only_the_current_frame_box(self):
        detection = ArtworkDetection(
            artwork_id="mona_lisa",
            label="Mona Lisa",
            confidence=0.91,
            bbox=(0.1, 0.2, 0.8, 0.9),
        )
        tracker = ArtworkTracker(
            ScriptedDetector([detection, None]), stability_frames=1
        )

        tracker.update()
        visual = tracker.visualization_status()
        assert visual["artwork_id"] == "mona_lisa"
        assert visual["bbox"] == (0.1, 0.2, 0.8, 0.9)

        tracker.update()
        assert tracker.visualization_status()["bbox"] is None


class TestManualOverride:
    def test_override_wins_over_vision(self):
        tracker = ArtworkTracker(ScriptedDetector([_det("mona_lisa")] * 5))
        tracker.set_manual_override("starry_night")
        result = tracker.update()
        assert result.artwork_id == "starry_night"
        assert result.source == "manual_override"
        assert result.stable is True

    def test_clear_override_restores_vision(self):
        tracker = ArtworkTracker(ScriptedDetector([_det("mona_lisa")] * 5))
        tracker.set_manual_override("starry_night")
        tracker.clear_manual_override()
        assert tracker.update().artwork_id == "mona_lisa"

    def test_status_reports_override(self):
        tracker = ArtworkTracker(ScriptedDetector([]))
        tracker.set_manual_override("tutankhamun_mask")
        status = tracker.status()
        assert status["manual_override"] is True
        assert status["artwork_id"] == "tutankhamun_mask"
        assert status["source"] == "manual_override"


class TestValidation:
    def test_unknown_artwork_id_rejected(self):
        tracker = ArtworkTracker(
            ScriptedDetector([_det("unknown_thing")]),
            valid_artwork_ids={"mona_lisa"},
        )
        assert tracker.update() is None

    def test_detector_error_treated_as_no_detection(self):
        class ExplodingDetector(BaseDetector):
            def detect(self, frame):
                raise RuntimeError("camera unplugged")

        tracker = ArtworkTracker(ExplodingDetector())
        assert tracker.update() is None
