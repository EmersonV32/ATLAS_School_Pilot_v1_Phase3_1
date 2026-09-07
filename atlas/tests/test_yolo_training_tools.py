"""Regression checks for the reproducible artwork-training utilities."""

from __future__ import annotations

import runpy
from pathlib import Path


def test_phone_dataset_targets_the_four_post_baseline_artworks():
    script = Path(__file__).parents[1] / "scripts" / "build_phone_yolo_dataset.py"
    namespace = runpy.run_path(str(script))

    assert namespace["NEW_ARTWORKS"] == {
        "girl_with_a_pearl_earring": 0,
        "great_wave_off_kanagawa": 1,
        "liberty_leading_the_people": 2,
        "sunflowers": 6,
    }
