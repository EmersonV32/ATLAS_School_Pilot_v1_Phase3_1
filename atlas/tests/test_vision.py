"""Tests for vision module."""
import pytest
from atlas.vision.detector import ArtworkDetection
from atlas.vision.mock_detector import MockDetector


def test_mock_detector_returns_detection():
    d = MockDetector()
    result = d.detect(frame=None)
    assert isinstance(result, ArtworkDetection)
    assert result.artwork_id
    assert 0.0 < result.confidence <= 1.0


def test_mock_detector_cycles_three_artworks():
    d = MockDetector()
    ids = [d.detect(None).artwork_id for _ in range(6)]
    assert ids[0] == ids[3]
    assert ids[1] == ids[4]
    assert ids[2] == ids[5]


def test_mock_detector_no_detect_every_fourth():
    d = MockDetector(always_detect=False)
    results = [d.detect(None) for _ in range(8)]
    # Calls 0 and 4 should be None (0 % 4 == 0, 4 % 4 == 0)
    assert results[0] is None
    assert results[4] is None
    assert results[1] is not None
    assert results[2] is not None


def test_is_confident_threshold():
    low = ArtworkDetection(artwork_id="x", label="X", confidence=0.3)
    high = ArtworkDetection(artwork_id="x", label="X", confidence=0.9)
    assert not low.is_confident
    assert high.is_confident
