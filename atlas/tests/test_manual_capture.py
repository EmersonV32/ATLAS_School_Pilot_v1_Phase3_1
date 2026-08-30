"""Tests for manual center-crop artwork capture."""

from __future__ import annotations

import numpy as np

from atlas.vision.manual_capture import (
    ManualArtworkCapture,
    center_crop,
    is_capture_command,
)


class FakeVisionClient:
    def __init__(self, answer: str | None = "mona_lisa") -> None:
        self.answer = answer
        self.image_jpeg = b""
        self.candidates: dict[str, str] = {}

    def identify_artwork(self, image_jpeg, candidates):
        self.image_jpeg = image_jpeg
        self.candidates = candidates
        return self.answer


def test_capture_commands_work_across_supported_languages():
    assert is_capture_command("Please capture this artwork")
    assert is_capture_command("Capture cette œuvre, s'il te plaît")
    assert is_capture_command("Identifica esta obra")
    assert is_capture_command("Cattura quest'opera")
    assert is_capture_command("請拍攝這件作品")
    assert not is_capture_command("Who painted this artwork?")


def test_center_crop_uses_requested_middle_region():
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    assert center_crop(frame, 0.5).shape == (50, 100, 3)


def test_manual_capture_encodes_in_memory_and_returns_stable_detection():
    client = FakeVisionClient()
    capture = ManualArtworkCapture(
        client=client,
        candidates={"mona_lisa": "Mona Lisa"},
        crop_ratio=0.5,
    )
    detection = capture.identify(np.zeros((120, 200, 3), dtype=np.uint8))
    assert detection is not None
    assert detection.artwork_id == "mona_lisa"
    assert detection.source == "manual_capture"
    assert detection.stable
    assert client.image_jpeg.startswith(b"\xff\xd8")


def test_manual_capture_rejects_unknown_answer():
    capture = ManualArtworkCapture(
        client=FakeVisionClient("unknown"),
        candidates={"mona_lisa": "Mona Lisa"},
    )
    assert capture.identify(np.zeros((20, 20, 3), dtype=np.uint8)) is None
