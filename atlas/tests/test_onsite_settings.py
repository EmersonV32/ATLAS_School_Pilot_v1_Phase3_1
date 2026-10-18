"""Onsite migration uses synthetic config only, never the installation's files."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).parents[1] / "scripts/prepare_onsite_settings.py"
SPEC = importlib.util.spec_from_file_location("onsite_settings", SCRIPT)
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


@pytest.fixture
def app_root(tmp_path):
    root = tmp_path / "application"
    (root / "src/atlas").mkdir(parents=True)
    (root / "config").mkdir()
    (root / "config/settings.yaml").write_text(
        "speech:\n  silero_min_silence_ms: 800\n  tts_provider: piper\n"
        "llm:\n  cloud_llm_enabled: false\nlogging:\n  log_transcripts: false\n"
        "hardware:\n  headset_name: Synthetic headset\n  enable_ev3: false\n"
        "camera_pan:\n  enabled: true\n  calibration_confirmed: true\n",
        encoding="utf-8",
    )
    return root


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_dry_run_never_changes_or_creates_files(app_root):
    base = app_root / "config/settings.yaml"
    original = base.read_bytes()
    assert setup.prepare(app_root, camera_host="192.168.3.9") is None
    assert base.read_bytes() == original
    assert not (app_root / "config/dashboard_overrides.yaml").exists()
    assert not (app_root / setup.BACKUP_FOLDER).exists()


def test_apply_preserves_unrelated_values_and_backs_up_both_files(app_root):
    base = app_root / "config/settings.yaml"
    override = app_root / "config/dashboard_overrides.yaml"
    override.write_text(
        "speech:\n  cloud_speech_enabled: false\n  silero_min_silence_ms: 700\n"
        "logging:\n  log_live_stt: false\ncustom:\n  marker: synthetic-only\n",
        encoding="utf-8",
    )
    old_base, old_override = base.read_bytes(), override.read_bytes()
    backup = setup.prepare(app_root, camera_host="atlas-camera.local", apply=True)
    assert (backup / base.name).read_bytes() == old_base
    assert (backup / override.name).read_bytes() == old_override
    for document in (load(base), load(override)):
        for key, value in setup.SPEECH_PATCH.items():
            assert document["speech"][key] == value
        assert document["camera_pan"]["enabled"] is False
        assert document["hardware"] == {
            **(
                {"headset_name": "Synthetic headset", "enable_ev3": False}
                if document is not None and "llm" in document
                else {}
            ),
            "camera_source": "http://atlas-camera.local:81/stream",
            "camera_control_url": "http://atlas-camera.local",
        }
    assert load(base)["speech"]["tts_provider"] == "piper"
    assert load(base)["llm"]["cloud_llm_enabled"] is False
    assert load(base)["logging"]["log_transcripts"] is False
    assert load(base)["camera_pan"]["calibration_confirmed"] is True
    assert load(override)["speech"]["cloud_speech_enabled"] is False
    assert load(override)["logging"]["log_live_stt"] is False
    assert load(override)["custom"]["marker"] == "synthetic-only"


@pytest.mark.parametrize("existing_override", [False, True])
def test_second_write_failure_restores_original_bytes(
    app_root, monkeypatch, existing_override
):
    base = app_root / "config/settings.yaml"
    override = app_root / "config/dashboard_overrides.yaml"
    if existing_override:
        override.write_text("logging: {log_transcripts: false}\n", encoding="utf-8")
    old_base = base.read_bytes()
    old_override = override.read_bytes() if existing_override else None
    original = setup._atomic_write

    def fail_second(path, contents, mode):
        if path == override:
            raise OSError("synthetic failure")
        return original(path, contents, mode)

    monkeypatch.setattr(setup, "_atomic_write", fail_second)
    with pytest.raises(setup.PreparationError, match="prior files were restored"):
        setup.prepare(app_root, apply=True)
    assert base.read_bytes() == old_base
    assert (
        override.read_bytes() == old_override
        if existing_override
        else not override.exists()
    )


@pytest.mark.parametrize(
    "contents", ["[a, b]", "null", "speech: [bad]", "speech: [", "x: 1\nx: 2"]
)
def test_invalid_yaml_refused_without_writes(app_root, contents):
    path = app_root / "config/settings.yaml"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(setup.PreparationError):
        setup.prepare(app_root, apply=True)
    assert path.read_text(encoding="utf-8") == contents
    assert not (app_root / setup.BACKUP_FOLDER).exists()


@pytest.mark.parametrize(
    "host",
    [
        "http://camera",
        "camera:81",
        "a/b",
        "x;echo secret",
        "x\nX: y",
        "x@camera",
        "-bad",
        "a..b",
        "256.2.2.2",
        "127.0.0.1",
        "::",
        "camera ",
    ],
)
def test_rejects_host_injection_and_unsafe_addresses(host):
    with pytest.raises(setup.PreparationError):
        setup.camera_endpoints(host)


@pytest.mark.parametrize(
    "host,authority",
    [
        ("192.168.2.9", "192.168.2.9"),
        ("atlas-camera.local", "atlas-camera.local"),
        ("fd00::9", "[fd00::9]"),
    ],
)
def test_camera_host_updates_both_correct_ports(host, authority):
    assert setup.camera_endpoints(host) == {
        "camera_source": f"http://{authority}:81/stream",
        "camera_control_url": f"http://{authority}",
    }


def test_custom_override_path_requires_review(app_root):
    path = app_root / "config/settings.yaml"
    path.write_text("dashboard: {config_override_path: other.yaml}\n", encoding="utf-8")
    with pytest.raises(setup.PreparationError, match="separate review"):
        setup.prepare(app_root, apply=True)


@pytest.mark.parametrize("existing_override", [False, True])
def test_failure_after_second_replace_rolls_back_both_files(
    app_root, monkeypatch, existing_override
):
    base = app_root / "config/settings.yaml"
    override = app_root / "config/dashboard_overrides.yaml"
    if existing_override:
        override.write_text("logging: {log_transcripts: false}\n", encoding="utf-8")
    old_base = base.read_bytes()
    old_override = override.read_bytes() if existing_override else None
    original = setup._atomic_write
    failed = False

    def fail_after_replace(path, contents, mode):
        nonlocal failed
        original(path, contents, mode)
        if path == override and not failed:
            failed = True
            raise OSError("Synthetic exception after atomic replacement")

    monkeypatch.setattr(setup, "_atomic_write", fail_after_replace)
    with pytest.raises(setup.PreparationError, match="prior files were restored"):
        setup.prepare(app_root, apply=True)
    assert base.read_bytes() == old_base
    if existing_override:
        assert override.read_bytes() == old_override
    else:
        assert not override.exists()


def test_failed_rollback_is_reported_as_incomplete(app_root, monkeypatch):
    original = setup._atomic_write
    calls = 0

    def fail_update_and_restore(path, contents, mode):
        nonlocal calls
        calls += 1
        if calls >= 2:
            raise OSError("Synthetic write unavailable")
        return original(path, contents, mode)

    monkeypatch.setattr(setup, "_atomic_write", fail_update_and_restore)
    with pytest.raises(setup.PreparationError, match="ROLLBACK INCOMPLETE"):
        setup.prepare(app_root, apply=True)


def test_metadata_detected_symlink_is_always_refused(app_root, monkeypatch):
    original = Path.is_symlink
    unsafe = app_root / "config/dashboard_overrides.yaml"
    monkeypatch.setattr(
        Path, "is_symlink", lambda path: path == unsafe or original(path)
    )
    with pytest.raises(setup.PreparationError, match="Symlinks"):
        setup.prepare(app_root, apply=True)


def test_symlink_refused(app_root, tmp_path):
    external = tmp_path / "outside.yaml"
    external.write_text("logging: {}\n", encoding="utf-8")
    override = app_root / "config/dashboard_overrides.yaml"
    try:
        override.symlink_to(external)
    except OSError:
        pytest.skip("This Windows account cannot create symbolic links")
    with pytest.raises(setup.PreparationError, match="Symlinks"):
        setup.prepare(app_root, apply=True)
    assert external.read_text(encoding="utf-8") == "logging: {}\n"


def test_cli_summary_never_prints_existing_values(app_root, capsys):
    assert setup.main(["--root", str(app_root)]) == 0
    output = capsys.readouterr().out
    assert "Synthetic headset" not in output
    assert "tts_provider" not in output
    assert "Environment overrides can still win" in output
    assert "HTTP 200 alone" in output
