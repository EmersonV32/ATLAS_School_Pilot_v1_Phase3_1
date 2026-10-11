"""Early startup guards using only synthetic adapters and local sockets."""

from __future__ import annotations

import errno
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from atlas.app.device_runtime import DeviceRuntime

START_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/start_device.sh"


def runtime(*, enabled=True, host="127.0.0.1", port=9876):
    return DeviceRuntime(
        SimpleNamespace(
            settings=SimpleNamespace(
                hardware=SimpleNamespace(),
                dashboard=SimpleNamespace(enabled=enabled, host=host, port=port),
            )
        )
    )


class StopAfterGuard(Exception):
    pass


@pytest.mark.parametrize(
    "family,address",
    [
        (socket.AF_INET, ("127.0.0.1", 12345)),
        (socket.AF_INET6, ("::1", 23456, 0, 0)),
    ],
)
def test_probe_respects_resolved_family_and_nondefault_port(
    monkeypatch,
    family,
    address,
):
    resolved, opened, bound, closed = [], [], [], []

    def lookup(*args):
        resolved.append(args)
        entry = (family, socket.SOCK_STREAM, 0, "", address)
        return [entry, entry]  # Duplicate resolver records need one probe.

    class Probe:
        def __init__(self, *args):
            opened.append(args)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            closed.append(True)

        def setsockopt(self, *_args):
            pass

        def bind(self, value):
            bound.append(value)

    monkeypatch.setattr("atlas.app.device_runtime.socket.getaddrinfo", lookup)
    monkeypatch.setattr("atlas.app.device_runtime.socket.socket", Probe)
    runtime(host=address[0], port=address[1])._check_dashboard_port_available()
    assert resolved[0][:2] == (address[0], address[1])
    assert opened == [(family, socket.SOCK_STREAM, 0)]
    assert bound == [address]
    assert closed == [True]


@pytest.mark.parametrize(
    "failure",
    [
        OSError(errno.EADDRINUSE, "synthetic busy port"),
        OSError(errno.EADDRNOTAVAIL, "synthetic nonlocal address"),
    ],
)
def test_bind_failure_closes_probe_and_skips_all_preload(monkeypatch, failure):
    closed, preloaded = [], []

    class Probe:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            closed.append(True)

        def setsockopt(self, *_args):
            pass

        def bind(self, _address):
            raise failure

    monkeypatch.setattr(
        "atlas.app.device_runtime.socket.getaddrinfo",
        lambda *_args: [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 43210))
        ],
    )
    monkeypatch.setattr("atlas.app.device_runtime.socket.socket", lambda *_: Probe())
    instance = runtime(port=43210)
    monkeypatch.setattr(instance, "preload", lambda: preloaded.append(True))
    with pytest.raises(RuntimeError, match="Dashboard address.*unavailable"):
        instance.run()
    assert preloaded == []
    assert closed == [True]


@pytest.mark.parametrize(
    "result",
    [
        [],
        socket.gaierror("synthetic invalid host"),
        ValueError("invalid port"),
    ],
)
def test_invalid_resolver_result_blocks_preload(monkeypatch, result):
    def lookup(*_args):
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr("atlas.app.device_runtime.socket.getaddrinfo", lookup)
    instance = runtime()
    monkeypatch.setattr(
        instance, "preload", lambda: pytest.fail("must not preload invalid bind")
    )
    with pytest.raises(RuntimeError, match="Check its host/port"):
        instance.run()


def test_disabled_dashboard_preserves_preload_flow_without_socket(monkeypatch):
    instance = runtime(enabled=False)
    monkeypatch.setattr(
        "atlas.app.device_runtime.socket.getaddrinfo",
        lambda *_: pytest.fail("disabled dashboard must not probe sockets"),
    )

    def preload():
        raise StopAfterGuard

    monkeypatch.setattr(instance, "preload", preload)
    with pytest.raises(StopAfterGuard):
        instance.run()


def test_loopback_listener_is_rejected_before_preload(monkeypatch):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        instance = runtime(port=listener.getsockname()[1])
        monkeypatch.setattr(
            instance, "preload", lambda: pytest.fail("occupied socket must fail early")
        )
        with pytest.raises(RuntimeError, match="Dashboard address.*unavailable"):
            instance.run()


def test_available_loopback_probe_releases_port_for_actual_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    runtime(port=port)._check_dashboard_port_available()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", port))


@pytest.mark.parametrize(
    "unsupported",
    [
        errno.EADDRNOTAVAIL,
        errno.EAFNOSUPPORT,
        errno.EPROTONOSUPPORT,
    ],
)
@pytest.mark.parametrize("ipv4_available", [True, False])
def test_resolved_family_fallback_requires_one_usable_address(
    monkeypatch,
    unsupported,
    ipv4_available,
):
    attempts, closed = [], []

    class Probe:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            closed.append(True)

        def setsockopt(self, *_args):
            pass

        def bind(self, address):
            attempts.append(address)
            if address[0] == "::1" or not ipv4_available:
                raise OSError(unsupported, "synthetic unavailable bind candidate")

    ipv6 = ("::1", 43210, 0, 0)
    ipv4 = ("127.0.0.1", 43210)
    monkeypatch.setattr(
        "atlas.app.device_runtime.socket.getaddrinfo",
        lambda *_: [
            (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ipv6),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ipv4),
        ],
    )
    monkeypatch.setattr("atlas.app.device_runtime.socket.socket", lambda *_: Probe())
    instance = runtime(host="localhost", port=43210)
    if ipv4_available:
        instance._check_dashboard_port_available()
    else:
        monkeypatch.setattr(
            instance, "preload", lambda: pytest.fail("must not preload invalid bind")
        )
        with pytest.raises(RuntimeError, match="Dashboard address.*unavailable"):
            instance.run()
    assert attempts == [ipv6, ipv4]
    assert closed == [True, True]


@pytest.mark.parametrize("port", [-1, 65536, "bad-port"])
def test_invalid_port_rejected_without_resolving_or_preloading(monkeypatch, port):
    monkeypatch.setattr(
        "atlas.app.device_runtime.socket.getaddrinfo",
        lambda *_: pytest.fail("invalid port must not be resolved or wrapped"),
    )
    instance = runtime(port=port)
    monkeypatch.setattr(
        instance, "preload", lambda: pytest.fail("invalid port must not preload")
    )
    with pytest.raises(RuntimeError, match="Check its host/port"):
        instance.run()


def bash_program():
    if sys.platform == "win32":
        program = Path("C:/Program Files/Git/bin/bash.exe")
        if program.is_file():
            return str(program)
    return shutil.which("bash")


@pytest.mark.parametrize("state", ["active", "inactive", "unavailable", "absent"])
def test_launcher_guard_before_activation_with_optional_systemd(state):
    bash = bash_program()
    if not bash:
        pytest.skip("Bash unavailable; shell guard checked where Bash is installed")
    source = START_SCRIPT.read_text(encoding="utf-8")
    guard = source[
        source.index("if command -v systemctl") : source.index('cd "$PROJECT_DIR"')
    ]
    if state == "absent":
        stub = "command() { return 1; }; systemctl() { echo UNEXPECTED; return 0; };"
    else:
        status = 0 if state == "active" else (1 if state == "inactive" else 3)
        stub = f"systemctl() {{ return {status}; }};"
    result = subprocess.run(
        [
            bash,
            "-c",
            "set -euo pipefail; " + stub + guard + "printf 'ACTIVATION_REACHED\\n'",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert "UNEXPECTED" not in result.stdout
    if state == "active":
        assert result.returncode == 1
        assert "ACTIVATION_REACHED" not in result.stdout
        assert "already running through atlas.service" in result.stderr
    else:
        assert result.returncode == 0
        assert "ACTIVATION_REACHED" in result.stdout


def test_launcher_guard_precedes_environment_activation():
    source = START_SCRIPT.read_text(encoding="utf-8")
    assert source.index("if command -v systemctl") < source.index(
        'source "$ATLAS_VENV_PATH'
    )
