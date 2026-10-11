"""A prebuilt engine can be promoted only with exact checkpoint provenance."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from atlas.vision.model_artifacts import (
    engine_matches_checkpoint,
    write_engine_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "promote_staged_engine", ROOT / "scripts/promote_staged_engine.py"
)
promoter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promoter)


@pytest.mark.parametrize("fault", [None, "checkpoint", "engine", "size", "missing"])
def test_promotion_validates_before_overwriting_live_engine(tmp_path, fault):
    stage = tmp_path / "stage"
    (stage / "models").mkdir(parents=True)
    staged_model = stage / "models/atlas_yolo.pt"
    staged_engine = stage / "models/atlas_yolo.engine"
    staged_model.write_bytes(b"new PT")
    staged_engine.write_bytes(b"new engine")
    write_engine_manifest(staged_model, staged_engine, 416)
    live_model = tmp_path / "atlas_yolo.pt"
    live_engine = live_model.with_suffix(".engine")
    live_model.write_bytes(b"new PT")
    live_engine.write_bytes(b"old engine")
    if fault == "checkpoint":
        live_model.write_bytes(b"different PT")
    elif fault == "engine":
        staged_engine.write_bytes(b"different engine")
    elif fault == "missing":
        staged_engine.unlink()
    size = 640 if fault == "size" else 416
    if fault:
        with pytest.raises(ValueError):
            promoter.promote_staged_engine(stage, live_model, size)
        assert live_engine.read_bytes() == b"old engine"
    else:
        assert promoter.promote_staged_engine(stage, live_model, size) == live_engine
        assert live_engine.read_bytes() == b"new engine"
        assert engine_matches_checkpoint(live_model, live_engine, 416)
