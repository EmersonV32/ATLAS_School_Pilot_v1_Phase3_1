#!/usr/bin/env python3
"""Allowlisted source-only release; no installs, secrets, models, or unit edits.

Build/verify work offline. Preflight/apply run ON the approved Linux target using
its existing interpreter and user service. The external SHA-256 is a transport
integrity check, not a signature: transfer it through the trusted operator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from urllib.request import urlopen

MANIFEST = "SOURCE_RELEASE.json"
FORMAT = "atlas-source-only-v1"
MAX_FILE = 20 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_FILES = 5000
EXACT = {
    "pyproject.toml",
    "scripts/run_deployment_pytest.py",
    "scripts/check_camera_pan_pwm.py",
    "scripts/start_device.sh",
    "scripts/configure_personal_wifi.py",
    "scripts/prepare_onsite_settings.py",
    "scripts/deploy/source_release.py",
}
VALIDATION_PREFIX = "validation/"
VALIDATION_SOURCE = "data/content_packs/demo_pack/"
VALIDATION_FILES = {VALIDATION_SOURCE + "manifest.json"} | {
    VALIDATION_SOURCE + f"artworks/{name}.json"
    for name in (
        "girl_with_a_pearl_earring",
        "great_wave_off_kanagawa",
        "liberty_leading_the_people",
        "mona_lisa",
        "starry_night",
        "sunflowers",
        "tutankhamun_mask",
    )
}
REQUIRED = (
    EXACT
    | {
        "src/atlas/__init__.py",
        "src/atlas/app/main.py",
        "src/atlas/dashboard/api.py",
        "src/atlas/dashboard/static/admin.js",
        "src/atlas/dashboard/templates/index.html",
        "tests/test_pipeline.py",
        "tests/test_speech_cancellation.py",
        "tests/test_listening_workflow.py",
        "tests/test_camera_source.py",
        "tests/test_visitor_dashboard.py",
        "tests/test_conversation_workflow.py",
        "tests/test_camera_pan.py",
        "tests/test_jetson_camera_pan.py",
    }
    | {VALIDATION_PREFIX + name for name in VALIDATION_FILES}
)
SMOKE_TESTS = (
    "tests/test_pipeline.py",
    "tests/test_speech_cancellation.py",
    "tests/test_listening_workflow.py",
    "tests/test_camera_source.py",
    "tests/test_visitor_dashboard.py",
    "tests/test_conversation_workflow.py",
    "tests/test_camera_pan.py",
    "tests/test_jetson_camera_pan.py",
)
ASSETS = (
    "/static/admin.js",
    "/static/visitor/assets/atlas-logo-v2.webp",
)


class ReleaseError(RuntimeError):
    """An operator-actionable failure without private subprocess output."""


def digest_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def allowed(path: str) -> bool:
    parts = PurePosixPath(path).parts
    if (
        not parts
        or "/".join(parts) != path
        or any(not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", p) for p in parts)
        or any(p in {".", "..", "__pycache__"} for p in parts)
    ):
        return False
    suffix = PurePosixPath(path).suffix
    return (
        path in EXACT
        or path in {VALIDATION_PREFIX + name for name in VALIDATION_FILES}
        or (
            path.startswith("src/atlas/")
            and suffix
            in {
                ".py",
                ".html",
                ".css",
                ".js",
                ".json",
                ".svg",
                ".webmanifest",
                ".webp",
            }
        )
        or (path.startswith("tests/") and suffix in {".py", ".h", ".cpp"})
    )


def no_links(path: Path, stop: Path) -> None:
    """Refuse symlinks/junctions in every existing component, not just leaves."""
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
            raise ReleaseError("Symlink/junction deployment paths are not allowed")
        if candidate == stop:
            break
    else:
        raise ReleaseError("Path leaves the approved directory")


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )
    return result.stdout


def build(source: Path, output: Path) -> dict:
    source = source.absolute()
    no_links(source, source.anchor and Path(source.anchor))
    if output.exists() or not output.parent.is_dir():
        raise ReleaseError("Output must be a new file in an existing directory")
    tracked = git_output(source, "ls-files", "-z", "--", ".").split("\0")
    sources = {name: name for name in tracked if allowed(name)}
    sources.update(
        {VALIDATION_PREFIX + name: name for name in tracked if name in VALIDATION_FILES}
    )
    names = sorted(sources)
    if not REQUIRED.issubset(names):
        raise ReleaseError("Required release files must be staged/tracked first")
    if git_output(
        source, "diff", "--name-only", "HEAD", "--", *sources.values()
    ).strip():
        raise ReleaseError("Commit reviewed release source before building a package")
    records = []
    for name in names:
        path = source / sources[name]
        no_links(path, source)
        if not path.is_file() or path.stat().st_size > MAX_FILE:
            raise ReleaseError("Missing or oversized tracked release file")
        records.append(
            {"path": name, "size": path.stat().st_size, "sha256": digest_file(path)}
        )
    if len(records) > MAX_FILES or sum(r["size"] for r in records) > MAX_TOTAL:
        raise ReleaseError("Release exceeds source-only size bounds")
    manifest = {
        "format": FORMAT,
        "source_revision": git_output(source, "rev-parse", "HEAD").strip(),
        "files": records,
    }
    # Exclusive creation prevents overwriting an earlier approved artifact.
    created = False
    try:
        handle = output.open("xb")
        created = True
        with (
            handle,
            zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as archive,
        ):
            archive.writestr(MANIFEST, json.dumps(manifest, sort_keys=True))
            for record in records:
                archive.write(source / sources[record["path"]], record["path"])
    except BaseException:
        if created and output.exists():
            output.unlink()
        raise
    verify(output, digest_file(output))
    return manifest


def verify(archive_path: Path, expected_sha256: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ReleaseError("An external lowercase SHA-256 is required")
    if (
        archive_path.stat().st_size > MAX_TOTAL
        or digest_file(archive_path) != expected_sha256
    ):
        raise ReleaseError("Release archive checksum/size mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(infos) > MAX_FILES + 1 or len(set(names)) != len(names):
            raise ReleaseError("Duplicate or excessive archive entries")
        if MANIFEST not in names or archive.getinfo(MANIFEST).file_size > 1024 * 1024:
            raise ReleaseError("Missing or oversized release manifest")
        for info in infos:
            kind = stat.S_IFMT(info.external_attr >> 16)
            if (
                kind not in {0, stat.S_IFREG}
                or info.is_dir()
                or info.flag_bits & 1
                or info.file_size > MAX_FILE
                or (info.filename != MANIFEST and not allowed(info.filename))
            ):
                raise ReleaseError("Unknown/nonregular/encrypted archive entry")
        if sum(info.file_size for info in infos) > MAX_TOTAL:
            raise ReleaseError("Expanded release exceeds size bound")
        manifest = json.loads(archive.read(MANIFEST))
        if (
            not isinstance(manifest, dict)
            or set(manifest) != {"format", "source_revision", "files"}
            or manifest["format"] != FORMAT
            or not re.fullmatch(r"[0-9a-f]{40}", str(manifest["source_revision"]))
            or not isinstance(manifest["files"], list)
        ):
            raise ReleaseError("Unsupported release manifest")
        listed = set()
        for record in manifest["files"]:
            if not isinstance(record, dict) or set(record) != {
                "path",
                "size",
                "sha256",
            }:
                raise ReleaseError("Malformed release file record")
            name, size, checksum = record["path"], record["size"], record["sha256"]
            if (
                not isinstance(name, str)
                or not allowed(name)
                or name in listed
                or type(size) is not int
                or not 0 <= size <= MAX_FILE
                or not isinstance(checksum, str)
                or not re.fullmatch(r"[0-9a-f]{64}", checksum)
                or name not in names
                or archive.getinfo(name).file_size != size
                or hashlib.sha256(archive.read(name)).hexdigest() != checksum
            ):
                raise ReleaseError("Release file mismatch")
            listed.add(name)
        if listed | {MANIFEST} != set(names) or not REQUIRED.issubset(listed):
            raise ReleaseError("Partial or unlisted release contents")
    return manifest


def extract(archive_path: Path, stage: Path, manifest: dict) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        for record in manifest["files"]:
            target = stage / record["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            content = archive.read(record["path"])
            if (
                len(content) != record["size"]
                or hashlib.sha256(content).hexdigest() != record["sha256"]
            ):
                raise ReleaseError("Archive changed after verification")
            with target.open("xb") as handle:
                handle.write(content)
            target.chmod(0o644)


class UserService:
    def __init__(self, root: Path, python: Path, unit: str = "atlas.service"):
        if unit != "atlas.service":
            raise ReleaseError("Only the existing atlas.service user unit is supported")
        self.root, self.python, self.unit = root, python, unit

    def command(self, *args: str) -> str:
        result = subprocess.run(
            ["systemctl", "--user", *args, self.unit],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode:
            raise ReleaseError("User service operation failed; inspect locally")
        return result.stdout

    def inspect(self) -> bool:
        values = dict(
            line.split("=", 1)
            for line in self.command(
                "show", "--property=LoadState,ActiveState,WorkingDirectory,ExecStart"
            ).splitlines()
            if "=" in line
        )
        if values.get("LoadState") != "loaded":
            raise ReleaseError("Existing user service is not loaded")
        if values.get("WorkingDirectory") != str(self.root):
            raise ReleaseError("Unit working directory differs from approved target")
        launch = values.get("ExecStart", "")
        if (
            f"path={self.python} ;" not in launch
            or f"argv[]={self.python} -m atlas.app.main " not in launch
        ):
            raise ReleaseError("Unit interpreter/launch differs from approved target")
        state = values.get("ActiveState")
        if state not in {"active", "inactive"}:
            raise ReleaseError("Unit must be stably active or inactive before release")
        return state == "active"

    def stop(self) -> None:
        self.command("stop")
        if self.inspect():
            raise ReleaseError("Service did not stop; no source replacement permitted")

    def start(self) -> None:
        self.command("start")

    def ready(self) -> None:
        # UI/process smoke only. /health may say ok with unavailable hardware.
        for _attempt in range(30):
            try:
                if not self.inspect():
                    raise ReleaseError("Service exited during startup")
                with urlopen("http://127.0.0.1:8765/health", timeout=2) as response:
                    if json.loads(response.read(1024 * 1024)).get("status") != "ok":
                        raise ReleaseError("Dashboard process health check failed")
                for asset in ASSETS:
                    with urlopen(
                        f"http://127.0.0.1:8765{asset}", timeout=2
                    ) as response:
                        if response.status != 200 or not response.read(1):
                            raise ReleaseError("Dashboard asset check failed")
                return
            except (OSError, ValueError, ReleaseError):
                time.sleep(2)
        raise ReleaseError(
            "Service/UI startup smoke failed; physical status unverified"
        )


def target_paths(root: Path, python: Path, backups: Path) -> None:
    for path in (root, python, backups):
        if not path.is_absolute() or ".." in path.parts:
            raise ReleaseError(
                "Explicit absolute target paths without '..' are required"
            )
    no_links(root, Path(root.anchor))
    no_links(backups, Path(backups.anchor))
    if (
        len(root.parts) < 4
        or not (root / "src/atlas").is_dir()
        or not (root / "config/settings.yaml").is_file()
        or not python.is_file()
        or not os.access(python, os.X_OK)
        or not backups.is_dir()
        or backups == root
        or backups.is_relative_to(root)
        or root.is_relative_to(backups)
        or python.is_relative_to(root / "src")
        or root.stat().st_dev != backups.stat().st_dev
    ):
        raise ReleaseError("Target/interpreter/backup layout failed safety preflight")
    for relative in ("src/atlas", "tests", *sorted(EXACT)):
        target = root / relative
        no_links(target, root)
        if target.is_dir():
            for directory, subdirs, files in os.walk(target, followlinks=False):
                for name in subdirs + files:
                    no_links(Path(directory) / name, root)
                    if (Path(directory) / name).stat().st_dev != root.stat().st_dev:
                        raise ReleaseError("Managed paths span filesystem boundaries")


def validate_interpreter(root: Path, python: Path) -> None:
    # Finding a top-level spec does not import ATLAS, its config, or dotenv.
    result = subprocess.run(
        [
            str(python),
            "-c",
            "import importlib.util; print(importlib.util.find_spec('atlas').origin)",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    expected = root / "src/atlas/__init__.py"
    if result.returncode or result.stdout.strip() != str(expected):
        raise ReleaseError(
            "Existing interpreter does not resolve this ATLAS source tree"
        )


def prepare_validation(stage: Path) -> None:
    """Make public fixtures available only in the disposable validation tree."""
    source = stage / VALIDATION_PREFIX / "data"
    if not source.is_dir() or (stage / "data").exists():
        raise ReleaseError("Disposable public validation fixtures unavailable")
    no_links(source, stage)
    source.replace(stage / "data")


def validate_stage(stage: Path, python: Path) -> None:
    """Only synthetic tests; never discover the deployed root's .env or state."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(
            (
                "ATLAS_",
                "GOOGLE_",
                "GEMINI_",
                "DEEPGRAM_",
                "CARTESIA_",
                "OPENAI_",
                "KIMI_",
                "ANTHROPIC_",
                "HF_",
                "WANDB_",
            )
        )
    }
    environment.update(
        {
            "PYTHONPATH": str(stage / "src"),
            "PYTHONPYCACHEPREFIX": str(stage / "bytecode"),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "YOLO_OFFLINE": "true",
            "YOLO_AUTOINSTALL": "false",
        }
    )
    tests = repr(list(SMOKE_TESTS))
    expression = (
        "import sys; sys.path.insert(0,'scripts'); "
        "import run_deployment_pytest as gate; original=gate.pytest.main; "
        f"gate.pytest.main=lambda args: original(args+{tests}); "
        "raise SystemExit(gate.run_tests())"
    )
    for arguments in (
        ["-m", "pip", "check"],
        ["-m", "compileall", "-q", "src"],
        ["-c", expression],
    ):
        result = subprocess.run(
            [str(python), *arguments],
            cwd=stage,
            env=environment,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode:
            # Suppress captured output: synthetic failures can still include host paths.
            raise ReleaseError("Offline staged validation failed; source unchanged")


def install_transaction(
    stage: Path,
    root: Path,
    backup: Path,
    service: UserService,
    *,
    start_if_stopped: bool = False,
) -> dict:
    """Move reviewed roots only; retain old source for acceptance or rollback."""
    was_active = service.inspect()
    backup.mkdir(mode=0o700)
    managed = ["src/atlas", "tests", *sorted(EXACT)]
    saved, installed = [], []
    stopped = False
    try:
        service.stop()
        stopped = True
        for relative in managed:
            target, old, new = root / relative, backup / relative, stage / relative
            if target.exists():
                old.parent.mkdir(parents=True, exist_ok=True)
                target.replace(old)
                saved.append(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            new.replace(target)
            installed.append(relative)
        if was_active or start_if_stopped:
            service.start()
            service.ready()
        return {
            "backup": str(backup),
            "started": was_active or start_if_stopped,
            "physical_acceptance": "pending",
        }
    except BaseException as error:
        failures = []
        try:
            service.stop()
            stopped = True
        except Exception:
            failures.append("stop")
            stopped = False
        # Never replace files under a service we could not confirm stopped.
        if stopped:
            for relative in reversed(installed):
                target = root / relative
                try:
                    if target.is_dir():
                        shutil.rmtree(target)
                    elif target.exists():
                        target.unlink()
                except Exception:
                    failures.append("remove")
            for relative in reversed(saved):
                try:
                    (backup / relative).replace(root / relative)
                except Exception:
                    failures.append("restore")
            if not failures and was_active:
                try:
                    service.start()
                    service.ready()
                except Exception:
                    failures.append("restart")
        if failures:
            raise ReleaseError(
                f"ROLLBACK INCOMPLETE ({','.join(failures)}); retained backup: {backup}"
            ) from error
        raise ReleaseError(
            f"Release failed; original source/state restored: {backup}"
        ) from error


def deploy(
    archive: Path,
    checksum: str,
    root: Path,
    python: Path,
    backups: Path,
    *,
    apply: bool = False,
    start_if_stopped: bool = False,
) -> dict:
    if sys.platform != "linux":
        raise ReleaseError("Preflight/apply must run on the approved Linux Jetson")
    import fcntl

    manifest = verify(archive, checksum)
    target_paths(root, python, backups)
    validate_interpreter(root, python)
    service = UserService(root, python)
    service.inspect()
    # One lock per actual installation, independent of the chosen backup directory.
    lock_path = root / ".atlas-source-deployment.lock"
    no_links(lock_path, root)
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(
            prefix="atlas-source-stage-", dir=backups
        ) as tmp:
            stage = Path(tmp)
            extract(archive, stage, manifest)
            prepare_validation(stage)
            validate_stage(stage, python)
            if not apply:
                return {
                    "preflight": "passed",
                    "source_revision": manifest["source_revision"],
                    "physical_acceptance": "pending",
                    "service_changed": False,
                }
            stamp = time.strftime("%Y%m%d-%H%M%S")
            backup = backups / f"atlas-source-{stamp}-{uuid.uuid4().hex[:8]}"
            return install_transaction(
                stage, root, backup, service, start_if_stopped=start_if_stopped
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    builder = commands.add_parser("build", help="Prepare locally; no SSH or deployment")
    builder.add_argument("--source-root", type=Path, required=True)
    builder.add_argument("--output", type=Path, required=True)
    for command in ("verify", "preflight", "apply"):
        child = commands.add_parser(command)
        child.add_argument("--archive", type=Path, required=True)
        child.add_argument("--sha256", required=True)
        if command != "verify":
            child.add_argument("--root", type=Path, required=True)
            child.add_argument("--python", type=Path, required=True)
            child.add_argument("--backup-dir", type=Path, required=True)
        if command == "apply":
            child.add_argument(
                "--approve-stop-and-replace", action="store_true", required=True
            )
            child.add_argument("--start-if-stopped", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "build":
            manifest = build(args.source_root, args.output)
            result = {
                "archive": str(args.output),
                "sha256": digest_file(args.output),
                "files": len(manifest["files"]),
                "deployed": False,
            }
        elif args.command == "verify":
            manifest = verify(args.archive, args.sha256)
            result = {
                "verified": True,
                "files": len(manifest["files"]),
                "deployed": False,
            }
        else:
            result = deploy(
                args.archive,
                args.sha256,
                args.root,
                args.python,
                args.backup_dir,
                apply=args.command == "apply",
                start_if_stopped=getattr(args, "start_if_stopped", False),
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        ReleaseError,
        subprocess.SubprocessError,
        zipfile.BadZipFile,
    ) as error:
        # Never dump subprocess captures or live health/component payloads.
        print(f"Source release refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
