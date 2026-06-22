"""Deterministic mock detector — cycles demo artworks, no camera needed."""
from __future__ import annotations
from typing import Any, Optional
from .detector import ArtworkDetection, BaseDetector

_DEMO_ARTWORKS = [
    ArtworkDetection(artwork_id="starry_night",     label="The Starry Night",         confidence=0.92),
    ArtworkDetection(artwork_id="mona_lisa",         label="Mona Lisa",                confidence=0.88),
    ArtworkDetection(artwork_id="tutankhamun_mask",  label="Tutankhamun's Death Mask", confidence=0.85),
]


class MockDetector(BaseDetector):
    """
    Cycles through _DEMO_ARTWORKS on each call so tests are reproducible.
    always_detect=False: simulate no-detection every 4th call.
    """

    def __init__(self, always_detect: bool = True) -> None:
        self._call_count = 0
        self._always_detect = always_detect

    def detect(self, frame: Any) -> Optional[ArtworkDetection]:
        if not self._always_detect and self._call_count % 4 == 0:
            self._call_count += 1
            return None
        result = _DEMO_ARTWORKS[self._call_count % len(_DEMO_ARTWORKS)]
        self._call_count += 1
        return result
