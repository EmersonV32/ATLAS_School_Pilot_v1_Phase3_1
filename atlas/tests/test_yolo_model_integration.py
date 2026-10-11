"""Model swaps cannot silently serve an old engine or lose artwork mappings."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from atlas.app.dependency_container import Container
from atlas.config.loader import load_settings
from atlas.config.settings import HardwareSettings, Settings
from atlas.models.enums import RunMode
from atlas.vision.artwork_release import load_model_labels
from atlas.vision.mock_detector import MockDetector
from atlas.vision.model_artifacts import (
    engine_manifest_path,
    engine_matches_checkpoint,
    select_yolo_model,
    sha256_file,
    write_engine_manifest,
)
from atlas.vision.yolo_detector import YoloDetector

ROOT = Path(__file__).resolve().parents[1]
V6_SHA = "af11b2de376a5c54a1ee11e9765f91ecbf54a1f308a2a82f9106b00a78409731"


@pytest.fixture
def artifacts(tmp_path):
    checkpoint = tmp_path / "model.pt"
    engine = tmp_path / "model.engine"
    checkpoint.write_bytes(b"portable checkpoint")
    engine.write_bytes(b"generated engine")
    write_engine_manifest(checkpoint, engine, 416)
    return checkpoint, engine


@pytest.mark.parametrize(
    "fault",
    [None, "checkpoint", "engine", "size", "missing", "corrupt", "list", "schema"],
)
def test_engine_binding_fails_closed(artifacts, fault):
    checkpoint, engine = artifacts
    manifest = engine_manifest_path(engine)
    if fault == "checkpoint":
        checkpoint.write_bytes(b"replacement v6 checkpoint")
    elif fault == "engine":
        engine.write_bytes(b"different engine")
    elif fault == "missing":
        manifest.unlink()
    elif fault == "corrupt":
        manifest.write_text("invalid JSON")
    elif fault == "list":
        manifest.write_text("[]")
    elif fault == "schema":
        manifest.write_text(json.dumps({"schema_version": 999}))
    size = 640 if fault == "size" else 416
    assert engine_matches_checkpoint(checkpoint, engine, size) is (fault is None)


@pytest.mark.parametrize("backend", ["auto", "pytorch", "tensorrt"])
@pytest.mark.parametrize("stale", [False, True])
def test_container_uses_only_the_engine_exported_for_current_model(
    artifacts, backend, stale
):
    checkpoint, engine = artifacts
    if stale:
        checkpoint.write_bytes(b"new trained model")
    container = Container(
        Settings(
            mode=RunMode.DEVICE,
            hardware=HardwareSettings(
                yolo_model_path=str(checkpoint),
                yolo_tensorrt_path=str(engine),
                yolo_backend=backend,
                yolo_device="cpu",
            ),
        )
    )
    detector = container.vision_detector
    use_engine = not stale and backend != "pytorch"
    assert detector._model_path == str(engine if use_engine else checkpoint)
    assert detector._fallback_model_path == (str(checkpoint) if use_engine else None)
    assert detector._device == "cpu"


def test_missing_models_do_not_break_mock_mode():
    assert isinstance(Container(Settings()).vision_detector, MockDetector)
    assert Settings().hardware.yolo_device == 0
    assert select_yolo_model("missing.pt", "missing.engine", "auto", 416) == (
        "missing.pt", None
    )


def test_cpu_device_can_be_configured_without_changing_jetson_default(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("ATLAS_YOLO_DEVICE", "cpu")
    config = tmp_path / "config"
    config.mkdir()
    (config / "settings.yaml").write_text("{}\n")
    assert load_settings(config).hardware.yolo_device == "cpu"


@pytest.mark.parametrize("class_id", range(7))
def test_all_v6_class_ids_reach_the_correct_artwork(class_id):
    names = load_model_labels(ROOT / "config/artwork_labels.yaml")
    box = SimpleNamespace(conf=[0.85], cls=[class_id], xyxyn=[[0.2, 0.2, 0.8, 0.8]])
    model = SimpleNamespace(
        names=dict(enumerate(names)),
        predict=lambda *_args, **_kwargs: [
            SimpleNamespace(boxes=[box], names=dict(enumerate(names)))
        ],
    )
    detector = YoloDetector("unused.pt", device="cpu")
    detector._model = model
    detection = detector.detect(object())
    assert detection.artwork_id == names[class_id]
    assert detection.bbox == (0.2, 0.2, 0.8, 0.8)
    assert detection.center_score == 1.0
    assert detector.class_names == names


def test_valid_engine_failure_falls_back_to_current_checkpoint(artifacts, monkeypatch):
    checkpoint, engine = artifacts
    detector = YoloDetector(str(engine), fallback_model_path=str(checkpoint))
    loaded = []

    def load(path):
        loaded.append(path)
        if path == str(engine):
            raise RuntimeError("TensorRT unavailable in this stack")
        return SimpleNamespace(predict=lambda *_args, **_kwargs: [])

    monkeypatch.setattr(detector, "_load_and_warm", load)
    detector.warm_up()
    assert loaded == [str(engine), str(checkpoint)]
    assert detector.active_model_path == str(checkpoint)
    assert detector.detect(object()) is None


def test_export_records_binding_after_success(artifacts, monkeypatch):
    checkpoint, engine = artifacts
    engine_manifest_path(engine).unlink()
    spec = importlib.util.spec_from_file_location(
        "export_tensorrt", ROOT / "scripts/export_tensorrt.py"
    )
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    monkeypatch.setitem(
        sys.modules,
        "ultralytics",
        SimpleNamespace(
            YOLO=lambda _path: SimpleNamespace(export=lambda **_kw: engine)
        ),
    )
    monkeypatch.setattr(sys, "argv", ["export", "--model", str(checkpoint)])
    exporter.main()
    assert engine_matches_checkpoint(checkpoint, engine, 416)


def test_active_checkpoint_is_the_supplied_v6_and_manifest_matches():
    checkpoint = ROOT / "models/atlas_yolo.pt"
    assert sha256_file(checkpoint) == V6_SHA
    candidate = ROOT / "models/releases/2026-09-28-yolo26n-atlas-v6/best.pt"
    assert sha256_file(candidate) == V6_SHA
    assert (ROOT / "models/manifest.sha256").read_text().splitlines()[0] == (
        V6_SHA + "  atlas_yolo.pt"
    )


def test_previous_checkpoint_is_preserved_for_portable_rollback():
    rollback = ROOT / "models/releases/2026-09-07-camera-domain-rollback"
    expected = "5680d3a5fff21d482e579c47f0b19e030b6acbdefdfe5da188de9cc961a66bec"
    assert sha256_file(rollback / "atlas_yolo.pt") == expected
    assert (rollback / "manifest.sha256").read_text().strip() == (
        expected + "  atlas_yolo.pt"
    )


@pytest.mark.skipif(
    os.getenv("ATLAS_TEST_REAL_YOLO") != "1",
    reason="Opt-in real inference needs the separate CPU ML environment",
)
def test_active_v6_real_inference_and_tracker():
    spec = importlib.util.spec_from_file_location(
        "smoke_yolo_runtime", ROOT / "scripts/smoke_yolo_runtime.py"
    )
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    report = smoke.run_smoke_check()
    assert report["valid"], report
    assert report["checkpoint_sha256"] == V6_SHA
    assert not report["blank_has_detection"]
    assert not report["physical_camera_validated"]
    assert not report["tensorrt_validated"]
