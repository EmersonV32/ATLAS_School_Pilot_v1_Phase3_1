"""Exercise PowerShell build/upload policy with fake CLI and synthetic files."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def camera_builder(request):
    shell = shutil.which("pwsh") or shutil.which("powershell.exe")
    if shell is None:
        pytest.skip("PowerShell camera workflow is verified on the Windows laptop")
    # Keep the copied Windows sketch below legacy MAX_PATH and off OneDrive.
    temporary = tempfile.TemporaryDirectory(prefix="atlas-camera-test-")
    request.addfinalizer(temporary.cleanup)
    repo = Path(temporary.name) / "fixture-repository"
    firmware = repo / "atlas/firmware/xiao_camera"
    tools = repo / ".tools/arduino-cli"
    firmware.mkdir(parents=True)
    tools.mkdir(parents=True)
    source = (ROOT / "firmware/xiao_camera/build_and_flash.ps1").read_text()
    # Replace only the CLI executable in this copied fixture. No real Arduino,
    # credential, board or serial device is touched by these tests.
    source = source.replace('"arduino-cli.exe"', '"fake.ps1"')
    script = firmware / "build_and_flash.ps1"
    script.write_text(source, encoding="utf-8")
    for name in set(re.findall(r'"([\w.-]+\.(?:h|cpp|ino)(?:\.example)?)"', source)):
        (firmware / name).write_text("// synthetic fixture\n", encoding="utf-8")
    (tools / "arduino-cli.yaml").write_text("synthetic fixture", encoding="utf-8")
    (tools / "fake.ps1").write_text(
        """
$ErrorActionPreference = 'Stop'
if ($args[0] -eq 'core') {
    Write-Output '{"platforms":[{"id":"esp32:esp32","installed_version":"3.3.11"}]}'
    exit 0
}
if ($args[0] -eq 'compile') {
    $index = [Array]::IndexOf($args, '--build-path')
    $build = $args[$index + 1]
    New-Item -ItemType Directory -Path $build -Force | Out-Null
    $names = @('xiao_camera.ino.bin', 'xiao_camera.ino.bootloader.bin',
               'xiao_camera.ino.partitions.bin')
    foreach ($name in $names) {
        [IO.File]::WriteAllBytes((Join-Path $build $name), [byte[]](1, 2, 3))
    }
    Write-Output 'SYNTHETIC-PRIVATE-DIAGNOSTIC'
    exit 0
}
if ($args[0] -eq 'upload') {
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'upload-invoked'), 'synthetic')
    Write-Output 'SYNTHETIC-PRIVATE-DIAGNOSTIC'
    exit 0
}
exit 2
""",
        encoding="utf-8",
    )

    def invoke(*arguments):
        try:
            result = subprocess.run(
                [
                    shell,
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script),
                    *arguments,
                ],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                cwd=repo,
                timeout=45,
            )
        except subprocess.TimeoutExpired as exc:
            pytest.fail(f"Synthetic builder timeout: {exc.stdout!r} / {exc.stderr!r}")
        assert "SYNTHETIC-PRIVATE-DIAGNOSTIC" not in result.stdout + result.stderr
        return result

    return firmware, tools, repo / ".tools/atlas-camera-release", invoke


def test_build_only_then_cached_upload_never_compiles_again(camera_builder):
    firmware, tools, cache, invoke = camera_builder
    built = invoke("-BuildOnly")
    assert built.returncode == 0, built.stderr
    assert "No camera flashed" in built.stdout
    assert not (tools / "upload-invoked").exists()
    selected = json.loads((cache / "current.json").read_text())["name"]
    prepared = cache / selected
    manifest = (prepared / "manifest.json").read_bytes()
    uploaded = invoke("-UploadOnly", "-Port", "SYNTHETIC-COM")
    assert uploaded.returncode == 0, uploaded.stderr
    assert (tools / "upload-invoked").exists()
    assert (prepared / "manifest.json").read_bytes() == manifest
    assert (firmware / "wifi_personal_secrets.h").read_text().startswith("// synthetic")


@pytest.mark.parametrize("change", ["source", "personal", "home", "binary", "missing"])
def test_cached_upload_refuses_stale_or_tampered_build(camera_builder, change):
    firmware, tools, cache, invoke = camera_builder
    built = invoke("-BuildOnly")
    assert built.returncode == 0, built.stderr
    selected = json.loads((cache / "current.json").read_text())["name"]
    if change == "source":
        (firmware / "xiao_camera.ino").write_text("changed public fixture")
    elif change == "personal":
        (firmware / "wifi_personal_secrets.h").write_text("changed synthetic fixture")
    elif change == "home":
        (firmware / "wifi_home_secrets.h").write_text("changed synthetic home fixture")
    else:
        binary = cache / selected / "build/xiao_camera.ino.bin"
        if change == "binary":
            binary.write_bytes(b"tampered synthetic fixture")
        else:
            binary.unlink()
    refused = invoke("-UploadOnly", "-Port", "SYNTHETIC-COM")
    assert refused.returncode != 0
    assert not (tools / "upload-invoked").exists()


def test_upload_without_build_and_conflicting_flags_are_refused(camera_builder):
    _firmware, tools, _cache, invoke = camera_builder
    assert invoke("-UploadOnly").returncode != 0
    assert invoke("-UploadOnly", "-BuildOnly").returncode != 0
    assert not (tools / "upload-invoked").exists()
