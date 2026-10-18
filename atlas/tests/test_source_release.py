"""Synthetic archives and fake services only; never touch the real installation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/deploy/source_release.py"
SPEC = importlib.util.spec_from_file_location("source_release", SCRIPT)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


@pytest.fixture
def package_files():
    return {name: f"synthetic {name}".encode() for name in release.REQUIRED}


def write_package(path, files, *, mutate=None, extras=()):
    manifest = {
        "format": release.FORMAT,
        "source_revision": "a" * 40,
        "files": [
            {
                "path": name,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for name, data in sorted(files.items())
        ],
    }
    if mutate:
        mutate(manifest)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(release.MANIFEST, json.dumps(manifest))
        for name, data in files.items():
            archive.writestr(name, data)
        for info, data in extras:
            archive.writestr(info, data)
    return release.digest_file(path)


@pytest.mark.parametrize(
    "path",
    [
        "../src/atlas/main.py",
        "/src/atlas/main.py",
        "src//atlas/main.py",
        "src/atlas/../outside.py",
        "src\\atlas\\main.py",
        "C:/src/atlas/main.py",
        "src/atlas/.env",
        "src/atlas/__pycache__/x.py",
        "config/settings.yaml",
        "models/atlas_yolo.engine",
        "firmware/xiao_camera/wifi_personal_secrets.h",
        ".private-network/atlas-personal.nmconnection",
        "scripts/atlas.service",
        "data/logs/runtime.py",
        "src/atlas/dump.sqlite",
        "src/atlas/private.log",
    ],
)
def test_private_unmanaged_and_traversal_paths_are_not_allowlisted(path):
    assert not release.allowed(path)


def test_valid_package_extracts_only_approved_source(tmp_path, package_files):
    archive = tmp_path / "release.zip"
    checksum = write_package(archive, package_files)
    manifest = release.verify(archive, checksum)
    stage = tmp_path / "stage"
    stage.mkdir()
    release.extract(archive, stage, manifest)
    assert {
        p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()
    } == set(package_files)
    assert not (stage / ".env").exists()


@pytest.mark.parametrize(
    "fault",
    [
        "checksum",
        "missing",
        "unlisted",
        "traversal",
        "symlink",
        "duplicate",
        "bad_hash",
        "bad_size",
        "bad_manifest",
        "bad_format",
        "bad_revision",
    ],
)
def test_malformed_packages_are_rejected(tmp_path, package_files, fault):
    archive = tmp_path / "release.zip"
    extras = []
    mutate = None
    if fault == "missing":
        package_files.pop("src/atlas/app/main.py")
    elif fault == "unlisted":
        extras = [("src/atlas/unlisted.py", b"unlisted")]
    elif fault == "traversal":
        extras = [("../escaped.py", b"escape")]
    elif fault == "symlink":
        link = zipfile.ZipInfo("src/atlas/link.py")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        extras = [(link, b"../../outside")]
    elif fault == "duplicate":
        extras = [("src/atlas/app/main.py", b"duplicate")]
    else:

        def mutate(value):
            if fault == "bad_hash":
                value["files"][0]["sha256"] = "0" * 64
            elif fault == "bad_size":
                value["files"][0]["size"] = True
            elif fault == "bad_manifest":
                value["extra"] = "unknown"
            elif fault == "bad_format":
                value["format"] = "wrong-format"
            elif fault == "bad_revision":
                value["source_revision"] = "HEAD"

    checksum = write_package(archive, package_files, mutate=mutate, extras=extras)
    if fault == "checksum":
        checksum = "0" * 64
    with pytest.raises(release.ReleaseError):
        release.verify(archive, checksum)
    assert not (tmp_path / "escaped.py").exists()


def test_changed_archive_is_rejected_during_extract(tmp_path, package_files):
    archive = tmp_path / "release.zip"
    checksum = write_package(archive, package_files)
    manifest = release.verify(archive, checksum)
    package_files["src/atlas/app/main.py"] = b"changed after verification"
    write_package(archive, package_files)
    stage = tmp_path / "stage"
    stage.mkdir()
    with pytest.raises(release.ReleaseError, match="changed"):
        release.extract(archive, stage, manifest)


def test_public_validation_fixtures_remain_disposable(tmp_path, package_files):
    archive = tmp_path / "release.zip"
    checksum = write_package(archive, package_files)
    stage = tmp_path / "stage"
    stage.mkdir()
    release.extract(archive, stage, release.verify(archive, checksum))
    release.prepare_validation(stage)
    assert (stage / "data/content_packs/demo_pack/manifest.json").is_file()
    assert not (stage / "validation/data").exists()
    assert "data/content_packs/demo_pack/manifest.json" not in release.EXACT
    with pytest.raises(release.ReleaseError, match="fixtures unavailable"):
        release.prepare_validation(stage)


def test_builder_reads_only_tracked_allowlist_and_will_not_overwrite(
    tmp_path,
    package_files,
    monkeypatch,
):
    source, output = tmp_path / "source", tmp_path / "release.zip"
    source.mkdir()
    for name, data in package_files.items():
        path = source / name.removeprefix(release.VALIDATION_PREFIX)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    untrusted_names = [".env", "data/logs/live.jsonl", "config/settings.yaml"]

    # These do not even exist. Reading an unapproved tracked path would fail.
    def fake_git(_root, *args):
        if args[0] == "ls-files":
            return (
                "\0".join(
                    [
                        *(
                            name.removeprefix(release.VALIDATION_PREFIX)
                            for name in package_files
                        ),
                        *untrusted_names,
                    ]
                )
                + "\0"
            )
        if args[0] == "diff":
            return ""
        return "a" * 40

    monkeypatch.setattr(release, "git_output", fake_git)
    manifest = release.build(source, output)
    assert {r["path"] for r in manifest["files"]} == set(package_files)
    original = output.read_bytes()
    with pytest.raises(release.ReleaseError, match="new file"):
        release.build(source, output)
    assert output.read_bytes() == original


class FakeService:
    def __init__(self, active, failure="none"):
        self.active, self.failure = active, failure
        self.calls = []
        self.failed = False

    def inspect(self):
        return self.active

    def fail_once(self, stage):
        if self.failure == stage and not self.failed:
            self.failed = True
            raise release.ReleaseError(f"synthetic {stage} failure")

    def stop(self):
        self.calls.append("stop")
        self.fail_once("stop")
        if self.failure == "rollback_stop" and len(self.calls) > 2:
            raise release.ReleaseError("cannot stop for rollback")
        self.active = False

    def start(self):
        self.calls.append("start")
        self.fail_once("start")
        self.active = True

    def ready(self):
        self.calls.append("ready")
        if self.failure == "rollback_stop":
            raise release.ReleaseError("synthetic health failure")
        self.fail_once("ready")


@pytest.fixture
def transaction(tmp_path, package_files):
    root, stage, backup = tmp_path / "device", tmp_path / "stage", tmp_path / "backup"
    old = {
        "src/atlas/obsolete.py": b"old source",
        "tests/test_old.py": b"old test",
        **{name: b"old helper" for name in release.EXACT},
    }
    protected = {
        ".env": b"SYNTHETIC NOT A REAL SECRET",
        "config/settings.yaml": b"old settings",
        "config/dashboard_overrides.yaml": b"old overrides",
        "models/atlas_yolo.engine": b"synthetic model",
        "data/sqlite/session.db": b"synthetic db",
        "data/logs/session.log": b"synthetic log",
        "firmware/xiao_camera/wifi_personal_secrets.h": b"synthetic header",
        "scripts/atlas.service": b"preserved unit",
        ".venv/keep": b"preserved interpreter",
    }
    for directory, files in ((root, {**old, **protected}), (stage, package_files)):
        for name, content in files.items():
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    return root, stage, backup, old, protected


@pytest.mark.parametrize("active", [False, True])
def test_success_preserves_original_service_state_and_all_private_state(
    transaction, active
):
    root, stage, backup, old, protected = transaction
    service = FakeService(active)
    result = release.install_transaction(stage, root, backup, service)
    assert service.active == active
    assert result["physical_acceptance"] == "pending"
    assert not (root / "src/atlas/obsolete.py").exists()
    assert (root / "src/atlas/app/main.py").is_file()
    assert not (root / "validation").exists()
    for name, content in protected.items():
        assert (root / name).read_bytes() == content
    for name, content in old.items():
        assert (backup / name).read_bytes() == content
    assert service.calls[0] == "stop"
    assert "start" in service.calls if active else "start" not in service.calls


@pytest.mark.parametrize("active", [False, True])
@pytest.mark.parametrize("failure", ["stop", "move", "start", "ready"])
def test_every_failed_stage_restores_original_source_and_state(
    transaction,
    active,
    failure,
    monkeypatch,
):
    root, stage, backup, old, protected = transaction
    service = FakeService(active, failure)
    replace = Path.replace
    failed_move = False

    def injected_move(path, destination):
        nonlocal failed_move
        if failure == "move" and path == stage / "tests" and not failed_move:
            failed_move = True
            raise OSError("synthetic install failure after source replacement")
        return replace(path, destination)

    monkeypatch.setattr(Path, "replace", injected_move)
    with pytest.raises(release.ReleaseError, match="original source/state restored"):
        release.install_transaction(stage, root, backup, service, start_if_stopped=True)
    assert service.active == active
    for name, content in {**old, **protected}.items():
        assert (root / name).read_bytes() == content, name
    assert not (root / "src/atlas/app/main.py").exists()
    assert not (root / "tests/test_pipeline.py").exists()


def test_incomplete_rollback_does_not_replace_files_under_running_service(transaction):
    root, stage, backup, _old, protected = transaction
    service = FakeService(True, "rollback_stop")
    with pytest.raises(release.ReleaseError, match="ROLLBACK INCOMPLETE"):
        release.install_transaction(stage, root, backup, service)
    assert (root / "src/atlas/app/main.py").exists()
    assert (backup / "src/atlas/obsolete.py").exists()
    assert service.calls.count("start") == 1
    for name, content in protected.items():
        assert (root / name).read_bytes() == content


def test_explicit_start_is_required_for_originally_stopped_service(transaction):
    root, stage, backup, _old, _protected = transaction
    service = FakeService(False)
    result = release.install_transaction(
        stage, root, backup, service, start_if_stopped=True
    )
    assert result["started"] is True
    assert service.active


def test_user_service_rejects_wrong_directory_or_interpreter(monkeypatch):
    service = release.UserService(
        PurePosixPath("/home/person/atlas"),
        PurePosixPath("/home/person/venv/bin/python"),
    )
    state = {
        "LoadState": "loaded",
        "ActiveState": "active",
        "WorkingDirectory": "/home/person/atlas",
        "ExecStart": (
            "{ path=/home/person/venv/bin/python ; "
            "argv[]=/home/person/venv/bin/python -m atlas.app.main --mode device ; }"
        ),
    }
    monkeypatch.setattr(
        service,
        "command",
        lambda *_args: "\n".join(f"{k}={v}" for k, v in state.items()),
    )
    assert service.inspect()
    state["WorkingDirectory"] = "/different/root"
    with pytest.raises(release.ReleaseError, match="working directory"):
        service.inspect()
    state["WorkingDirectory"] = "/home/person/atlas"
    state["ExecStart"] = "{ path=/bin/bash ; argv[]=/bin/bash -c unspecified ; }"
    with pytest.raises(release.ReleaseError, match="interpreter/launch"):
        service.inspect()


def test_validation_sanitizes_environment_and_uses_isolated_dotenv_wrapper(
    tmp_path,
    monkeypatch,
):
    calls = []
    monkeypatch.setenv("ATLAS_ADMIN_TOKEN", "synthetic")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "synthetic")

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(release.subprocess, "run", run)
    release.validate_stage(tmp_path, Path("/existing/python"))
    assert len(calls) == 3
    for command, options in calls:
        assert command[0] == str(Path("/existing/python"))
        assert options["cwd"] == tmp_path
        assert "ATLAS_ADMIN_TOKEN" not in options["env"]
        assert "DEEPGRAM_API_KEY" not in options["env"]
    assert "run_deployment_pytest" in calls[-1][0][-1]
    assert "install" not in " ".join(calls[0][0])


def test_cli_apply_requires_explicit_approval(monkeypatch):
    monkeypatch.setattr(
        release.sys,
        "argv",
        [
            "source_release.py",
            "apply",
            "--archive",
            "dummy.zip",
            "--sha256",
            "a" * 64,
            "--root",
            "/home/person/atlas",
            "--python",
            "/home/person/venv/bin/python",
            "--backup-dir",
            "/home/person/backups",
        ],
    )
    with pytest.raises(SystemExit):
        release.main()
