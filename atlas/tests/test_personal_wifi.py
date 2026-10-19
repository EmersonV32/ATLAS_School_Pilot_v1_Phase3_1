"""Personal network preparation uses synthetic credentials and mock nmcli only."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import warnings
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "personal_wifi_setup",
    ROOT / "scripts/configure_personal_wifi.py",
)
setup = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = setup
SPEC.loader.exec_module(setup)


@pytest.fixture
def config():
    return setup.PersonalConfig("fixture network", ' $fixture;\\" password ')


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ssid", ""),
        ("ssid", "é" * 17),
        ("ssid", "bad\nssid"),
        ("password", "short"),
        ("password", "é" * 9),
        ("password", "x" * 64),
        ("password", "bad\x00input"),
        ("security", "enterprise"),
        ("profile_uuid", "not-a-uuid"),
    ],
)
def test_invalid_personal_values_do_not_render(config, field, value):
    with pytest.raises(ValueError):
        setup.render_camera_header(replace(config, **{field: value}))


@pytest.mark.parametrize("security", ["auto", "wpa3"])
def test_camera_literals_preserve_dollars_quotes_and_slashes(config, security):
    text = setup.render_camera_header(replace(config, security=security))
    for key, value in [("SSID", config.ssid), ("PASSWORD", config.password)]:
        line = next(line for line in text.splitlines() if f"PERSONAL_{key}[]" in line)
        assert json.loads(line.split(" = ", 1)[1].removesuffix(";")) == value
    assert f"WPA3_ONLY = {str(security == 'wpa3').lower()};" in text
    assert "username" not in text.lower()


def test_private_config_representation_does_not_expose_either_value(config):
    assert config.ssid not in repr(config)
    assert config.password not in repr(config)


def test_wpa3_uses_the_same_portable_camera_passphrase_limit(config):
    with pytest.raises(ValueError):
        setup.validate(replace(config, security="wpa3", password="short"))


def test_raw_hex_key_is_only_valid_in_auto_mode(config):
    setup.validate(replace(config, password="a" * 64))
    with pytest.raises(ValueError):
        setup.validate(replace(config, security="wpa3", password="a" * 64))


@pytest.mark.parametrize("security", ["auto", "wpa3"])
def test_private_profile_round_trip_is_inactive_and_nonenterprise(
    config,
    security,
    tmp_path,
):
    config = replace(config, ssid="tést; wifi", security=security)
    rendered = setup.render_jetson_profile(config)
    path = tmp_path / "fixture.nmconnection"
    path.write_text(rendered, encoding="utf-8")
    assert setup.read_import_profile(path) == config
    assert "autoconnect=false" in rendered
    assert "autoconnect-priority=200" in rendered
    assert "method=auto" in rendered
    assert "802-1x" not in rendered
    assert "username" not in rendered
    assert (
        "key-mgmt=sae" in rendered
        if security == "wpa3"
        else "key-mgmt=wpa-psk" in rendered
    )


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("autoconnect=false", "autoconnect=true"),
        ("key-mgmt=wpa-psk", "key-mgmt=wpa-eap"),
        ("pmf=2", "pmf=1"),
        ("method=auto", "method=manual"),
        ("id=ATLAS-personal", "id=Other-network"),
        ("proto=rsn;", "proto=wpa;"),
        ("[ipv4]", "[ipv4]\nroutes=10.0.0.0/8"),
    ],
)
def test_import_refuses_unapproved_network_policy(config, tmp_path, old, new):
    path = tmp_path / "fixture.nmconnection"
    path.write_text(
        setup.render_jetson_profile(config).replace(old, new), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        setup.read_import_profile(path)


def test_default_write_never_overwrites_existing_header(config, tmp_path):
    path = tmp_path / "wifi_personal_secrets.h"
    path.write_text("synthetic old personal settings")
    with pytest.raises(ValueError, match="already exist"):
        setup.write_private_files({path: setup.render_camera_header(config)})
    assert path.read_text() == "synthetic old personal settings"
    assert list(tmp_path.iterdir()) == [path]


def test_explicit_replace_keeps_recoverable_private_backup(tmp_path):
    path = tmp_path / "wifi_personal_secrets.h"
    path.write_text("synthetic old")
    result = setup.write_private_files({path: "synthetic new"}, replace_existing=True)
    assert path.read_text() == "synthetic new"
    assert result[path].read_text() == "synthetic old"
    if os.name == "posix":
        assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("preexisting", [False, True])
def test_partial_batch_failure_rolls_back_both_files(
    tmp_path, monkeypatch, preexisting
):
    first, second = tmp_path / "first.h", tmp_path / "second.nmconnection"
    if preexisting:
        first.write_text("old first")
        second.write_text("old second")
    original = setup.os.replace

    def fail_second(source, destination):
        if Path(destination) == second and ".pending-" in Path(source).name:
            raise OSError("Synthetic install failure")
        original(source, destination)

    monkeypatch.setattr(setup.os, "replace", fail_second)
    with pytest.raises(OSError):
        setup.write_private_files(
            {first: "new first", second: "new second"},
            replace_existing=preexisting,
        )
    if preexisting:
        assert first.read_text() == "old first" and second.read_text() == "old second"
    else:
        assert not first.exists() and not second.exists()
    assert not list(tmp_path.glob("*.pending-*"))


def test_install_stages_only_one_profile_and_no_active_connection(
    config,
    tmp_path,
    monkeypatch,
):
    calls = []

    def command(*args):
        calls.append(args)
        return "old-hotspot" if args[1:3] == ("NAME", "connection") else ""

    monkeypatch.setattr(setup, "nmcli", command)
    assert setup.install_jetson(config, tmp_path) == config.profile_uuid
    assert calls[-1] == ("connection", "load", str(tmp_path / setup.PROFILE_FILE))
    assert not any("up" in call or "modify" in call for call in calls)
    assert all(
        config.password not in str(call) and config.ssid not in str(call)
        for call in calls
    )


def test_imported_uuid_cannot_replace_or_delete_another_network(
    config,
    tmp_path,
    monkeypatch,
):
    def command(*args):
        if args[:2] == ("-g", "NAME"):
            return "unrelated network"
        if args[:2] == ("-g", "UUID"):
            return config.profile_uuid
        pytest.fail("No changing command is permitted for an unrelated UUID")

    monkeypatch.setattr(setup, "nmcli", command)
    with pytest.raises(ValueError, match="another saved connection"):
        setup.install_jetson(config, tmp_path)
    assert not list(tmp_path.iterdir())


def test_failed_profile_load_removes_only_this_new_profile(
    config, tmp_path, monkeypatch
):
    unrelated = tmp_path / "unrelated.nmconnection"
    unrelated.write_text("synthetic untouched")
    calls = []

    def command(*args):
        calls.append(args)
        if args[:2] == ("connection", "load"):
            raise subprocess.CalledProcessError(1, ["nmcli"])
        return ""

    monkeypatch.setattr(setup, "nmcli", command)
    with pytest.raises(subprocess.SubprocessError):
        setup.install_jetson(config, tmp_path)
    assert unrelated.read_text() == "synthetic untouched"
    assert not (tmp_path / setup.PROFILE_FILE).exists()
    assert calls[-1] == ("connection", "delete", "uuid", config.profile_uuid)


def test_prepare_prompts_once_for_both_devices_without_echo_or_external_commands(
    config,
    tmp_path,
    monkeypatch,
    capsys,
):
    camera_dir = tmp_path / "firmware/xiao_camera"
    camera_dir.mkdir(parents=True)
    for filename in ("wifi_secrets.h", "wifi_school_secrets.h"):
        (camera_dir / filename).write_text("synthetic unchanged")
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["setup", "--target", "prepare"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    values = iter([config.ssid, config.password, config.password])
    monkeypatch.setattr(setup, "hidden_input", lambda _prompt: next(values))
    monkeypatch.setattr(
        setup.subprocess, "run", lambda *_a, **_k: pytest.fail("no commands")
    )
    assert setup.main() == 0
    output = capsys.readouterr().out
    assert config.password not in output and config.ssid not in output
    assert (camera_dir / "wifi_personal_secrets.h").exists()
    assert (tmp_path / ".private-network" / setup.PROFILE_FILE).exists()
    for filename in ("wifi_secrets.h", "wifi_school_secrets.h"):
        assert (camera_dir / filename).read_text() == "synthetic unchanged"


def test_noninteractive_and_remote_activation_are_rejected(monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys, "argv", ["setup", "--target", "prepare"])
    with pytest.raises(SystemExit):
        setup.main()
    monkeypatch.setenv("SSH_CONNECTION", "synthetic-remote-session")
    monkeypatch.setattr(
        sys, "argv", ["setup", "--target", "jetson", "--activate", "--local-console"]
    )
    with pytest.raises(SystemExit):
        setup.main()


def test_getpass_echo_fallback_aborts_before_password_input(monkeypatch):
    def echo_fallback(_prompt):
        warnings.warn("Cannot hide input", getpass.GetPassWarning, stacklevel=2)

    import getpass

    monkeypatch.setattr(setup.getpass, "getpass", echo_fallback)
    with pytest.raises(getpass.GetPassWarning):
        setup.hidden_input("Synthetic hidden prompt")


def test_new_personal_credentials_are_ignored_and_recovery_excluded():
    ignore = (ROOT.parent / ".gitignore").read_text()
    assert "**/wifi_personal_secrets.h" in ignore
    assert "**/.private-network/" in ignore
    assert "**/*.nmconnection" in ignore
    assert "**/wifi_home_secrets.h" in ignore
    assert "**/wifi_home_secrets.h.backup-*" in ignore
    assert "**/.wifi_home_secrets.h.pending-*" in ignore


@pytest.mark.parametrize("security", ["auto", "wpa3"])
def test_home_header_preserves_the_same_safe_encoding(config, security):
    text = setup.render_home_header(replace(config, security=security))
    assert "WIFI_PERSONAL_" not in text
    for key, value in [("SSID", config.ssid), ("PASSWORD", config.password)]:
        line = next(line for line in text.splitlines() if f"HOME_{key}[]" in line)
        assert json.loads(line.split(" = ", 1)[1].removesuffix(";")) == value


def test_home_declaration_names_never_rewrite_credential_values():
    config = setup.PersonalConfig(
        "WIFI_PERSONAL_fixture", "WIFI_PERSONAL_private-fixture"
    )
    text = setup.render_home_header(config)
    for key, value in [("SSID", config.ssid), ("PASSWORD", config.password)]:
        line = next(line for line in text.splitlines() if f"HOME_{key}[]" in line)
        assert json.loads(line.split(" = ", 1)[1].removesuffix(";")) == value


def test_home_setup_preserves_all_three_existing_profiles(
    config, tmp_path, monkeypatch, capsys
):
    camera_dir = tmp_path / "firmware/xiao_camera"
    camera_dir.mkdir(parents=True)
    originals = ("wifi_secrets.h", "wifi_school_secrets.h", "wifi_personal_secrets.h")
    for filename in originals:
        (camera_dir / filename).write_text("synthetic unchanged")
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["setup", "--target", "camera-home"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    values = iter([config.ssid, config.password, config.password])
    monkeypatch.setattr(setup, "hidden_input", lambda _prompt: next(values))
    assert setup.main() == 0
    output = capsys.readouterr().out
    assert config.password not in output and config.ssid not in output
    assert (
        "WIFI_HOME_CONFIGURED = true"
        in (camera_dir / "wifi_home_secrets.h").read_text()
    )
    assert not (tmp_path / ".private-network").exists()
    for filename in originals:
        assert (camera_dir / filename).read_text() == "synthetic unchanged"
