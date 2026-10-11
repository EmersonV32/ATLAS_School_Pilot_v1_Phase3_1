"""School preparation must preserve hotspot state and keep credentials private."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import warnings
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "school_wifi_setup", ROOT / "scripts/configure_school_wifi.py"
)
setup = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = setup
SPEC.loader.exec_module(setup)


@pytest.fixture
def candidate():
    return setup.SchoolConfig(
        "test-school",
        "fixture-user",
        'synthetic $ \\" value',
        "fixture-user",
        allow_unverified=True,
    )


def test_default_refuses_unverified_server(candidate):
    with pytest.raises(ValueError, match="verification"):
        setup.validate(replace(candidate, allow_unverified=False))


@pytest.mark.parametrize(
    "field,value",
    [
        ("ssid", ""),
        ("ssid", "é" * 17),
        ("ssid", "line\nbreak"),
        ("username", ""),
        ("username", "x" * 128),
        ("password", ""),
        ("password", "x" * 65),
        ("password", "bad\x00input"),
        ("identity", ""),
        ("identity", "x" * 128),
        ("identity", "bad\rinput"),
    ],
)
def test_invalid_values_rejected_without_rendering(candidate, field, value):
    with pytest.raises(ValueError):
        setup.render_camera_header(replace(candidate, **{field: value}))


@pytest.mark.parametrize("field", ["ca_pem", "server_name"])
def test_partial_trust_does_not_silently_downgrade(candidate, field):
    with pytest.raises(ValueError, match="both"):
        setup.validate(replace(candidate, **{field: "present"}))


def test_credentials_not_in_config_representation(candidate):
    assert candidate.username not in repr(candidate)
    assert candidate.password not in repr(candidate)


def test_camera_header_escapes_quotes_backslashes_and_preserves_dollars(candidate):
    header = setup.render_camera_header(candidate)
    line = next(line for line in header.splitlines() if "SCHOOL_PASSWORD[]" in line)
    assert json.loads(line.split(" = ", 1)[1].removesuffix(";")) == candidate.password
    assert "WIFI_SCHOOL_ALLOW_UNVERIFIED_SERVER = true;" in header


def test_jetson_profile_is_offline_and_handles_special_characters(candidate):
    config = replace(candidate, ssid="tést;school", password=" $x\\y ")
    text = setup.render_jetson_profile(config)
    assert "autoconnect=false" in text
    assert "autoconnect-priority=100" in text
    assert "autoconnect-retries=1" in text
    assert "auth-retries=2" in text
    assert "key-mgmt=wpa-eap" in text
    assert "eap=peap;" in text
    assert "phase2-auth=mschapv2" in text
    assert "password=\\s$x\\\\y\\s" in text
    assert "ssid=" + ";".join(map(str, config.ssid.encode())) + ";" in text
    assert "ca-cert=" not in text


def test_verified_profile_keeps_ca_and_exact_server_constraint(candidate, monkeypatch):
    monkeypatch.setattr(setup.ssl, "PEM_cert_to_DER_cert", lambda _: b"fixture-only")
    config = replace(
        candidate,
        ca_pem="public-CA-fixture",
        ca_path="/tmp/public-ca.crt",
        server_name="radius.example.invalid",
        allow_unverified=False,
    )
    assert "ALLOW_UNVERIFIED_SERVER = false" in setup.render_camera_header(config)
    profile = setup.render_jetson_profile(config)
    assert "ca-cert=/tmp/public-ca.crt" in profile
    assert "domain-match=radius.example.invalid" in profile
    with pytest.raises(ValueError):
        setup.render_jetson_profile(replace(config, ca_path="relative.crt"))
    with pytest.raises(ValueError):
        setup.validate(replace(config, ca_path="/tmp/a\nb.crt"))


def test_private_key_rejected_as_ca(candidate):
    config = replace(
        candidate, ca_pem="PRIVATE KEY", server_name="radius.example.invalid"
    )
    with pytest.raises(ValueError, match="private key"):
        setup.validate(config)


def test_existing_file_never_read_or_overwritten(tmp_path):
    target = tmp_path / "synthetic-private.h"
    target.write_text("synthetic-existing", encoding="utf-8")
    with pytest.raises(FileExistsError):
        setup.write_private_new(target, "replacement")
    assert target.read_text() == "synthetic-existing"


def test_private_new_file_has_restrictive_permissions_on_posix(tmp_path):
    target = tmp_path / "synthetic-private.h"
    setup.write_private_new(target, "synthetic-new")
    assert target.read_text() == "synthetic-new"
    if os.name == "posix":
        assert target.stat().st_mode & 0o777 == 0o600


def test_jetson_load_never_activates_or_passes_credentials_in_argv(
    candidate, tmp_path, monkeypatch
):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        assert kwargs["capture_output"]
        assert candidate.password not in args
        return SimpleNamespace(stdout="hotspot\n", returncode=0)

    monkeypatch.setattr(setup.subprocess, "run", fake_run)
    path = setup.install_jetson(candidate, tmp_path)
    assert path.exists()
    assert calls == [
        ["nmcli", "-g", "NAME", "connection", "show"],
        ["nmcli", "connection", "load", str(path)],
    ]


def test_existing_nm_profile_refused(candidate, tmp_path, monkeypatch):
    monkeypatch.setattr(
        setup.subprocess,
        "run",
        lambda *_a, **_k: SimpleNamespace(stdout="ATLAS-school\n"),
    )
    with pytest.raises(ValueError, match="already exists"):
        setup.install_jetson(candidate, tmp_path)
    assert not list(tmp_path.iterdir())


def test_failed_nm_load_removes_only_new_profile(candidate, tmp_path, monkeypatch):
    other = tmp_path / "existing-hotspot"
    other.write_text("synthetic-preserved")

    def fake_run(args, **_kwargs):
        if "load" in args:
            raise subprocess.CalledProcessError(1, args)
        return SimpleNamespace(stdout="hotspot\n")

    monkeypatch.setattr(setup.subprocess, "run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        setup.install_jetson(candidate, tmp_path)
    assert other.read_text() == "synthetic-preserved"
    assert not (tmp_path / "atlas-school.nmconnection").exists()


def test_noninteractive_setup_refused_before_any_credentials(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["setup", "--target", "camera"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(SystemExit) as error:
        setup.main()
    assert error.value.code == 2


def test_unverified_mode_requires_explicit_confirmation(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["setup", "--target", "camera", "--allow-unverified-server"]
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "no")
    monkeypatch.setattr(
        setup.getpass, "getpass", lambda _: pytest.fail("must not ask for credentials")
    )
    assert setup.main() == 1


def test_hidden_input_refuses_echo_fallback(monkeypatch):
    def no_secure_terminal(_prompt):
        warnings.warn("Cannot hide input", setup.getpass.GetPassWarning, stacklevel=2)
        pytest.fail("must stop before echoing fallback")

    monkeypatch.setattr(setup.getpass, "getpass", no_secure_terminal)
    with pytest.raises(setup.getpass.GetPassWarning):
        setup.hidden_input("Synthetic hidden prompt: ")


def test_camera_setup_success_is_local_only(tmp_path, monkeypatch, capsys, candidate):
    target = tmp_path / "firmware/xiao_camera"
    target.mkdir(parents=True)
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["setup", "--target", "camera", "--allow-unverified-server"]
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: setup.RISK_CONFIRMATION)
    values = iter([candidate.username, candidate.password])
    monkeypatch.setattr(setup, "hidden_input", lambda _: next(values))
    monkeypatch.setattr(
        setup.subprocess, "run", lambda *_a, **_k: pytest.fail("no external command")
    )
    assert setup.main() == 0
    assert (target / "wifi_school_secrets.h").exists()
    output = capsys.readouterr().out
    assert "Not flashed" in output
    assert candidate.username not in output
    assert candidate.password not in output


def test_missing_public_ca_fails_before_prompt_or_write(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "setup",
            "--target",
            "camera",
            "--ca-cert",
            str(tmp_path / "not-present.crt"),
            "--server-name",
            "radius.example.invalid",
        ],
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(setup, "hidden_input", lambda _: pytest.fail("must not prompt"))
    assert setup.main() == 1
    assert not list(tmp_path.iterdir())


def test_camera_profile_is_optional_and_fallback_is_personal():
    source = (ROOT / "firmware/xiao_camera/xiao_camera.ino").read_text()
    assert source.index("connectSchoolWifi(") < source.index(
        "WiFi.begin(WIFI_SSID, WIFI_PASSWORD)"
    )
    school = (ROOT / "firmware/xiao_camera/school_wifi.cpp").read_text()
    assert '__has_include("wifi_school_secrets.h")' in school
    assert "schoolWifiProfileUsable(kSchool)" in school
    assert "WiFi.scanDelete()" in school
    assert "esp_wifi_sta_enterprise_disable()" in school
    assert "esp_eap_client_set_eap_methods(ESP_EAP_TYPE_PEAP)" in school
    assert "esp_eap_client_set_domain_name(kSchool.serverName)" in school
    assert "esp_eap_client_set_disable_time_check(false)" in school
    assert "Serial.print(kSchool" not in school
    ignore = (ROOT.parent / ".gitignore").read_text()
    assert "**/wifi_school_secrets.h" in ignore
