"""Public-source firmware checks; no private header or physical device is opened."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
FIRMWARE = ROOT / "firmware/xiao_camera"


def test_primary_personal_selection_precedes_preserved_school_and_hotspot():
    source = (FIRMWARE / "xiao_camera.ino").read_text()
    assert source.index("connectPersonalWifi(") < source.index("connectSchoolWifi(")
    assert source.index("connectSchoolWifi(") < source.index("connectHomeWifi(")
    assert source.index("connectHomeWifi(") < source.index(
        "WiFi.begin(WIFI_SSID, WIFI_PASSWORD)"
    )
    assert '#include "wifi_secrets.h"' in source
    assert "nextWifiReconnectAtMs" not in source
    assert "cameraIntervalElapsed(now, lastWifiReconnectAtMs" in source
    assert "bool wifiRecoveryActive = false" in source


def test_optional_personal_profile_security_and_fallback():
    source = (FIRMWARE / "personal_wifi.cpp").read_text()
    assert '__has_include("wifi_personal_secrets.h")' in source
    assert "personalWifiProfileUsable(profile)" in source
    assert '__has_include("wifi_home_secrets.h")' in source
    assert 'connectProfile(kHome, "Home fallback"' in source
    assert 'connectProfile(kPersonal, "Primary personal"' in source
    assert "WiFi.scanDelete()" in source
    assert "auth == WIFI_AUTH_WPA2_ENTERPRISE" not in source
    assert "auth == WIFI_AUTH_OPEN" not in source
    assert "auth == WIFI_AUTH_WPA_PSK" not in source
    assert "config.sta.pmf_cfg.required = profile.wpa3Only" in source
    assert source.index("esp_wifi_set_config(") < source.index("esp_wifi_connect()")
    assert "WiFi.setMinSecurity(profile.wpa3Only ? WIFI_AUTH_WPA3_PSK" in source
    assert "Serial.print(profile" not in source
    template = (FIRMWARE / "wifi_personal_secrets.h.example").read_text()
    assert "WIFI_PERSONAL_CONFIGURED = false" in template
    assert 'WIFI_PERSONAL_SSID[] = ""' in template
    assert 'WIFI_PERSONAL_PASSWORD[] = ""' in template
    home = (FIRMWARE / "wifi_home_secrets.h.example").read_text()
    assert "WIFI_HOME_CONFIGURED = false" in home
    assert 'WIFI_HOME_SSID[] = ""' in home
    assert 'WIFI_HOME_PASSWORD[] = ""' in home
    build = (FIRMWARE / "build_and_flash.ps1").read_text()
    assert '"wifi_home_secrets.h.example"' in build
    assert '"wifi_home_secrets.h"' in build


def test_stream_shared_state_is_snapshotted_and_future_timestamp_is_guarded():
    source = (FIRMWARE / "app_httpd.cpp").read_text()
    assert "volatile bool isStreaming" not in source
    assert "portENTER_CRITICAL(&streamStateMux)" in source
    assert (
        "return cameraStreamStalledPolicy(active, nowMs, lastFrameMs, timeoutMs)"
        in source
    )
    assert "setStreamState(true, millis())" in source
    assert "setStreamState(false, 0)" in source


def test_client_cleanup_precedes_watchdog_and_radio_sleep_stays_off():
    source = (FIRMWARE / "app_httpd.cpp").read_text()
    assert "config.send_wait_timeout = kAtlasHttpWaitTimeoutS" in source
    assert "config.recv_wait_timeout = kAtlasHttpWaitTimeoutS" in source
    policy = (FIRMWARE / "camera_timing_policy.h").read_text()
    assert "kAtlasHttpWaitTimeoutS * 1000 < kAtlasStreamStallRestartMs" in policy
    assert "kAtlasIdleWifiPowerSave = false" in policy
    main = (FIRMWARE / "xiao_camera.ino").read_text()
    assert "kAtlasIdleWifiPowerSave && !cameraStreamActive()" in main


def test_synthetic_compile_does_not_copy_private_credentials():
    source = (ROOT / "scripts/verify_school_firmware.ps1").read_text()
    assert '"personal-auto"' in source
    assert '"personal-wpa3-with-school"' in source
    assert '"home-with-personal-school"' in source
    assert 'Join-Path $source "wifi_secrets.h.example"' in source
    assert 'Join-Path $source "wifi_secrets.h"' not in source
    assert 'Join-Path $source "wifi_personal_secrets.h"' not in source
    assert 'Join-Path $source "wifi_school_secrets.h"' not in source
    assert 'Join-Path $source "wifi_home_secrets.h"' not in source
    assert " upload " not in source


def test_native_cpp_timing_and_personal_policy_regressions():
    """Compile actual constexpr C++ policy, including wrap/race counterexamples."""
    compiler = shutil.which("g++") or shutil.which("clang++")
    if compiler is None:
        tools = Path.home() / "AppData/Local/Arduino15/packages/esp32/tools"
        compiler = next(
            (str(path) for path in tools.glob("*/**/xtensa-esp32s3-elf-g++.exe")),
            None,
        )
    if compiler is None:
        pytest.skip(
            "No C++ compiler installed; synthetic ESP32 build also compiles assertions"
        )
    result = subprocess.run(
        [
            compiler,
            "-std=c++14",
            "-fsyntax-only",
            "-I",
            str(FIRMWARE),
            str(ROOT / "tests/fixtures/camera_firmware_policy_checks.cpp"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
