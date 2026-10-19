"""Fault-inject the actual deploy transaction, using ONLY temporary files."""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def bash_executable():
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    candidate = str(git_bash) if git_bash.exists() else shutil.which("bash")
    if candidate is None:
        pytest.skip("Bash is required for deployment fault injection")
    return candidate


def bash_path(path):
    value = path.as_posix()
    return f"/{value[0].lower()}{value[2:]}" if path.drive else value


@pytest.mark.parametrize(
    "failure",
    [
        "none",
        "stop",
        "extract",
        "pytest",
        "checksum",
        "labels",
        "export",
        "restore_config",
        "install_unit",
        "reload",
        "start",
        "health",
        "asset",
    ],
)
@pytest.mark.parametrize("prebuilt", [False, True])
def test_deployment_rolls_back_every_failed_stage(tmp_path, failure, prebuilt):
    root = tmp_path / "device"
    backup = tmp_path / "backup"
    unit = tmp_path / "units/atlas.service"
    archive = tmp_path / "patch.tar.gz"
    staged = tmp_path / "staged"
    staged.mkdir()
    old = {
        "src/atlas/runtime.py": b"old runtime",
        "tests/test_old.py": b"old tests",
        "data/content_packs/demo_pack/manifest.json": b"old content",
        "config/settings.yaml": b"device-specific settings",
        "config/dashboard_overrides.yaml": b"device-specific overrides",
        "models/atlas_yolo.pt": b"old PT",
        "models/atlas_yolo.engine": b"old engine",
        "models/atlas_yolo.engine.manifest.json": b"old engine provenance",
        "models/atlas_yolo.onnx": b"old ONNX",
        "models/manifest.sha256": b"old manifest",
        "scripts/atlas.service": b"old packaged service",
    }
    for relative, data in old.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    unit.parent.mkdir()
    unit.write_bytes(b"old installed service")
    new = {
        "src/atlas/runtime.py": b"new runtime",
        "tests/test_new.py": b"new tests",
        "data/content_packs/demo_pack/manifest.json": b"new content",
        "config/settings.yaml": b"development settings",
        "models/atlas_yolo.pt": b"new PT",
        "models/manifest.sha256": b"0" * 64 + b"  atlas_yolo.pt\n",
        "scripts/atlas.service": b"new installed service",
        "scripts/restore_models.sh": (ROOT / "scripts/restore_models.sh").read_bytes(),
    }
    # Hash the synthetic checkpoint, never a live model or private file.
    if failure != "checksum":
        new["models/manifest.sha256"] = (
            hashlib.sha256(new["models/atlas_yolo.pt"]).hexdigest()
            + "  atlas_yolo.pt\n"
        ).encode()
    with tarfile.open(archive, "w:gz") as tar:
        for relative, data in new.items():
            member = tarfile.TarInfo(relative)
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
    script = (ROOT / "scripts/deploy/apply_visitor_patch.sh").read_text()
    # Validate all test mutation targets before substituting isolated paths.
    for path in (root, backup, unit, archive):
        assert path.resolve().is_relative_to(tmp_path.resolve())
    script = script.replace("__ROOT__", bash_path(root)).replace(
        "__ARCHIVE__", bash_path(archive)
    )
    script = script.replace("/tmp/atlas_visitor_backup___STAMP__", bash_path(backup))
    script = script.replace("__PYTHON__", "python_stub")
    script = script.replace("__STAGED_ROOT__", bash_path(staged) if prebuilt else "")
    script = script.replace(
        '[[ "$staged_root" == /tmp/atlas_v6_preflight_* '
        '&& "$(dirname "$staged_root")" == /tmp ]]',
        f'[[ "$staged_root" == "{bash_path(staged)}" ]]',
    )
    script = script.replace(
        'unit="$HOME/.config/systemd/user/atlas.service"', f"unit='{bash_path(unit)}'"
    )
    script = script.replace(
        '"$backup" == /tmp/atlas_visitor_backup_*',
        f'"$backup" == "{bash_path(backup)}"',
    )
    harness = r"""
export PATH="/usr/bin:/bin:$PATH"
failure='__FAILURE__'
failed_once=0
exported=0
fail_once() {
  if [[ "$failure" == "$1" && "$failed_once" -eq 0 ]]; then failed_once=1; return 42; fi
}
systemctl() {
  printf '%s\n' "$*" >> '__CALLS__'
  case "$*" in
    *is-active*) return 0;;
    *stop*) fail_once stop;;
    *daemon-reload*) fail_once reload;;
    *start*) fail_once start;;
  esac
}
tar() { command tar "$@"; fail_once extract; }
install() { command install "$@"; fail_once install_unit; }
cp() {
  if [[ "$exported" -eq 1 && "$*" == *device_settings.yaml* ]]; then
    fail_once restore_config || return $?
  fi
  command cp "$@"
}
python_stub() {
  # Dispatch on the script argument, not a staged path containing pytest-of-*.
  case "$1" in
    *pytest*) fail_once pytest;;
    *verify_yolo_checkpoint*) fail_once labels;;
    *export_tensorrt*|*promote_staged_engine*)
      printf 'new engine' > models/atlas_yolo.engine
      printf 'new engine provenance' > models/atlas_yolo.engine.manifest.json
      printf 'new ONNX' > models/atlas_yolo.onnx
      exported=1
      fail_once export;;
  esac
}
curl() {
  if [[ "$failure" == health && "$*" == *health* ]]; then return 42; fi
  if [[ "$failure" == asset && "$*" == *static* ]]; then return 42; fi
  return 0
}
sleep() { return 0; }
""".replace("__FAILURE__", failure).replace("__CALLS__", bash_path(tmp_path / "calls"))
    rendered = tmp_path / "deploy.sh"
    rendered.write_text(harness + script, encoding="utf-8", newline="\n")
    result = subprocess.run(
        [bash_executable(), rendered.as_posix()],
        text=True,
        capture_output=True,
        # Git Bash process startup/rollback copying is slower under Windows
        # compiler/antivirus load. This is a test deadline, not runtime policy.
        timeout=60 if os.name == "nt" else 20,
    )
    if failure == "none":
        assert result.returncode == 0, result.stdout + result.stderr
        assert (root / "src/atlas/runtime.py").read_bytes() == b"new runtime"
        assert (root / "models/atlas_yolo.engine").read_bytes() == b"new engine"
        assert (root / "models/atlas_yolo.engine.manifest.json").read_bytes() == (
            b"new engine provenance"
        )
        assert unit.read_bytes() == b"new installed service"
        assert "restoring backup" not in result.stderr
    else:
        assert result.returncode != 0
        for relative, data in old.items():
            assert (root / relative).read_bytes() == data, relative
        assert unit.read_bytes() == b"old installed service"
        assert not (root / "tests/test_new.py").exists()
        assert not (root / "scripts/restore_models.sh").exists()
        assert "ROLLBACK INCOMPLETE" not in result.stderr, result.stderr
        assert (
            (tmp_path / "calls")
            .read_text()
            .rstrip()
            .endswith("--user start atlas.service")
        )
    assert backup.is_dir()
    assert (root / "config/settings.yaml").read_bytes() == old["config/settings.yaml"]
    assert (root / "config/dashboard_overrides.yaml").read_bytes() == old[
        "config/dashboard_overrides.yaml"
    ]
