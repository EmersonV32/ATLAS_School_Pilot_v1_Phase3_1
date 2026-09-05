#!/usr/bin/env python3
"""Verify that Git contains everything needed to rebuild the ATLAS runtime."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "DEPLOY_ATLAS.ps1",
    "pyproject.toml",
    ".env.example",
    "requirements-jetson.lock.txt",
    "config/settings.yaml",
    "data/content_packs/demo_pack/manifest.json",
    "firmware/xiao_camera/wifi_secrets.h.example",
    "models/atlas_yolo.pt",
    "models/manifest.sha256",
    "scripts/atlas.service",
    "scripts/bootstrap_jetson.sh",
    "scripts/configure_cloud_keys.sh",
    "scripts/install_user_service.sh",
    "scripts/restore_models.sh",
    "src/atlas/app/main.py",
    "artwork-source/manifest.sha256",
    "artwork-source/mona-lisa.png",
    "artwork-source/great-wave.png",
    "artwork-source/ambassadors.png",
)
REPOSITORY_REQUIRED = (
    "README.md",
    "archive/README.md",
    "handoff/README.md",
    "handoff/START_HERE.md",
    "handoff/CURRENT_STATE.md",
    "handoff/LLM_HANDOFF.md",
    "handoff/REPOSITORY_MAP.md",
    "handoff/VALIDATION_CHECKLIST.md",
    "handoff/SECRETS_AND_PRIVATE_STATE.md",
    "handoff/TROUBLESHOOTING.md",
    "handoff/jetson/ARDUCAM_IMX477.md",
    "handoff/jetson/OPERATIONS_MANUAL.md",
    "handoff/jetson/REBUILD_FROM_FRESH_FLASH.md",
    ".github/workflows/recovery-gate.yml",
)
PRIVATE_OR_GENERATED = (
    ".env",
    "firmware/xiao_camera/wifi_secrets.h",
    "models/atlas_yolo.engine",
    "models/atlas_yolo.onnx",
    "models/silero_vad.onnx",
)
GENERATED_PREFIXES = ("data/chroma/", "data/sqlite/", "data/logs/")
FORBIDDEN_REPOSITORY_PREFIXES = ("codex-final-handoff/",)


def _git(*args: str, cwd: Path = PROJECT_ROOT) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_manifest(relative_manifest: str, failures: list[str]) -> None:
    manifest_path = PROJECT_ROOT / relative_manifest
    if not manifest_path.is_file():
        return
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        expected_hash, relative_name = line.split(maxsplit=1)
        asset_path = manifest_path.parent / relative_name.strip()
        display_path = asset_path.relative_to(PROJECT_ROOT).as_posix()
        if not asset_path.is_file():
            failures.append(f"manifest asset is missing: {display_path}")
        elif _sha256(asset_path) != expected_hash:
            failures.append(f"manifest hash mismatch: {display_path}")


def main() -> int:
    repository_root = Path(_git("rev-parse", "--show-toplevel").strip())
    project_prefix = PROJECT_ROOT.relative_to(repository_root).as_posix()
    tracked = set(_git("ls-files", cwd=repository_root).splitlines())
    failures: list[str] = []

    if project_prefix != "atlas":
        failures.append(
            f"active runtime must be repository-root atlas/, found: {project_prefix}"
        )

    for relative in REPOSITORY_REQUIRED:
        if not (repository_root / relative).is_file():
            failures.append(f"missing repository continuity file: {relative}")
        elif relative not in tracked:
            failures.append(f"repository continuity file is not tracked: {relative}")

    for relative in REQUIRED:
        repository_path = f"{project_prefix}/{relative}"
        if not (PROJECT_ROOT / relative).is_file():
            failures.append(f"missing required file: {relative}")
        elif repository_path not in tracked:
            failures.append(f"required file is not tracked: {relative}")

    for relative in PRIVATE_OR_GENERATED:
        repository_path = f"{project_prefix}/{relative}"
        if repository_path in tracked:
            failures.append(f"private/generated file is tracked: {relative}")

    for repository_path in tracked:
        if any(
            repository_path.startswith(prefix)
            for prefix in FORBIDDEN_REPOSITORY_PREFIXES
        ):
            failures.append(f"obsolete runtime path is tracked: {repository_path}")
        if not repository_path.startswith(f"{project_prefix}/"):
            continue
        relative = repository_path[len(project_prefix) + 1 :]
        if relative.endswith("/.gitkeep"):
            continue
        if any(relative.startswith(prefix) for prefix in GENERATED_PREFIXES):
            failures.append(f"generated runtime state is tracked: {relative}")

    _verify_manifest("models/manifest.sha256", failures)
    _verify_manifest("artwork-source/manifest.sha256", failures)

    if failures:
        print("Recovery bundle verification failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Recovery bundle verified: required files are tracked and portable.")
    print("Private secrets and generated Jetson artifacts remain excluded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
