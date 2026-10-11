"""The supplied-results path verifies bytes and metadata without unpickling."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import pickle
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "inspect_yolo_results", ROOT / "scripts/inspect_yolo_results.py"
)
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)


def checkpoint_bytes(names):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            "checkpoint/data.pkl",
            pickle.dumps({"names": dict(enumerate(names))}, protocol=2),
        )
    return stream.getvalue()


@pytest.fixture
def results(tmp_path):
    names = inspector.load_model_labels(ROOT / "config/artwork_labels.yaml")
    checkpoint = checkpoint_bytes(names)
    candidate = tmp_path / "best.pt"
    candidate.write_bytes(checkpoint)
    metric = {
        "map50": 0.9,
        "map50_95": 0.8,
        "per_class": {name: {"ap50": 0.9, "ap50_95": 0.8} for name in names},
    }
    report = {
        "checkpoint_sha256": hashlib.sha256(checkpoint).hexdigest(),
        "dataset": {"classes": names},
        "test_416": metric,
        "test_640": metric,
    }
    return tmp_path / "results.zip", candidate, checkpoint, report


@pytest.mark.parametrize(
    "fault", [None, "checkpoint", "candidate", "classes", "metrics", "duplicate"]
)
def test_results_inspector_fails_closed_on_mismatched_artifacts(results, fault):
    archive_path, candidate, checkpoint, report = results
    if fault == "checkpoint":
        report["checkpoint_sha256"] = "0" * 64
    elif fault == "candidate":
        candidate.write_bytes(b"different checkpoint")
    elif fault == "classes":
        report["dataset"]["classes"].reverse()
    elif fault == "metrics":
        report["test_416"]["map50"] = 0.1
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("results/best.pt", checkpoint)
        archive.writestr("results/atlas_evaluation.json", json.dumps(report))
        if fault == "duplicate":
            archive.writestr("other/best.pt", checkpoint)
    if fault:
        with pytest.raises(ValueError):
            inspector.inspect_results(
                archive_path, candidate, ROOT / "config/artwork_labels.yaml"
            )
    else:
        result = inspector.inspect_results(
            archive_path, candidate, ROOT / "config/artwork_labels.yaml"
        )
        assert result["metadata_verified"]
        assert not result["inference_verified"]
        assert not result["deployment_ready"]


def test_metadata_inspection_never_executes_pickle(tmp_path):
    marker = tmp_path / "must-not-exist"

    class ExecutablePickle:
        def __reduce__(self):
            return eval, (f"open({str(marker)!r}, 'w').write('executed')",)

    checkpoint = io.BytesIO()
    with zipfile.ZipFile(checkpoint, "w") as archive:
        archive.writestr(
            "checkpoint/data.pkl", pickle.dumps(ExecutablePickle(), protocol=2)
        )
    with pytest.raises(ValueError, match="class-name layout"):
        inspector.embedded_names(checkpoint.getvalue())
    assert not marker.exists()


@pytest.mark.parametrize("temp_environment", ["normal", "temp-unset"])
def test_prepare_only_bundle_selects_model_without_uploading(
    tmp_path, temp_environment
):
    script = ROOT / "scripts/deploy/DEPLOY_ATLAS_VISITOR_IMPROVEMENTS.ps1"
    if not script.is_file() or not (ROOT.parent / ".git").exists():
        pytest.skip("The deployment packager is tested from a full Git checkout")
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        pytest.skip("PowerShell is needed to verify the deployment packager")
    archive = tmp_path / "prepared.tar.gz"
    candidate = tmp_path / "selected.pt"
    candidate.write_bytes(b"synthetic selected checkpoint")
    environment = os.environ.copy()
    temporary_root = tmp_path / "controlled-temporary-directory"
    temporary_root.mkdir()
    environment["TEMP"] = str(temporary_root)
    environment["TMP"] = str(temporary_root)
    environment["TMPDIR"] = str(temporary_root)
    if temp_environment == "temp-unset":
        environment.pop("TEMP", None)
    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-File",
            str(script),
            "-PrepareOnly",
            "-YoloCheckpoint",
            str(candidate),
            "-PreparedArchivePath",
            str(archive),
            "-SshKeyPath",
            str(tmp_path / "does-not-exist"),
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "not uploaded or deployed" in result.stdout
    assert list(temporary_root.iterdir()) == []
    with tarfile.open(archive) as bundle:
        contents = {
            member.name.removeprefix("./"): member for member in bundle.getmembers()
        }
        assert (
            bundle.extractfile(contents["models/atlas_yolo.pt"]).read()
            == candidate.read_bytes()
        )
        manifest = (
            bundle.extractfile(contents["models/manifest.sha256"]).read().decode()
        )
        assert (
            manifest
            == hashlib.sha256(candidate.read_bytes()).hexdigest() + "  atlas_yolo.pt\n"
        )
        assert "scripts/deploy/apply_visitor_patch.sh" in contents
        assert "scripts/inspect_yolo_results.py" in contents
        assert "tests/test_handoff_regressions.py" in contents
        for required in (
            "models/releases/2026-09-28-yolo26n-atlas-v6/best.pt",
            "models/releases/2026-09-07-camera-domain-rollback/atlas_yolo.pt",
            "models/releases/2026-09-07-camera-domain-rollback/manifest.sha256",
            "scripts/build_phone_yolo_dataset.py",
            "scripts/run_deployment_pytest.py",
            "training/prepare_artwork_dataset_v5.py",
            "training/handoff/train.py",
            "artwork-source/mona-lisa.png",
            "artwork-source/great-wave.png",
        ):
            assert required in contents
        assert not any(name.endswith((".env", ".engine", ".onnx")) for name in contents)
