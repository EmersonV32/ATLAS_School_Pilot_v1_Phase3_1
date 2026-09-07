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


def test_v5_split_policy_keeps_reviewed_capture_ranges_apart():
    script = Path(__file__).parents[1] / "training" / "prepare_artwork_dataset_v5.py"
    namespace = runpy.run_path(str(script))
    assigned_split = namespace["assigned_split"]

    assert assigned_split("IMG_4700_jpeg") == "train"
    assert assigned_split("IMG_4400_jpeg") == "valid"
    assert assigned_split("IMG_4500_jpeg") == "test"
    assert assigned_split("IMG_6500_jpg") == "train"
    assert assigned_split("IMG_6750_jpg") == "valid"
    assert assigned_split("IMG_6860_jpg") is None
    assert assigned_split("IMG_6900_jpg") == "test"
    assert assigned_split("photo-1779645220000_jpg") == "train"
    assert assigned_split("photo-1788376400000_jpg") == "test"


def test_v5_training_recipe_matches_camera_domain():
    script = Path(__file__).parents[1] / "training" / "handoff" / "train.py"
    namespace = runpy.run_path(str(script))
    overrides = namespace["TRAINING_OVERRIDES"]

    assert namespace["RUN_NAME"] == "yolo26n-atlas-v5-camera"
    assert overrides["perspective"] > 0
    assert overrides["degrees"] > 0
    assert overrides["fliplr"] == 0
    assert 0 < overrides["mosaic"] < 1
