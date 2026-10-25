"""Explicit, bounded SG90 experiment; default invocation only prints a plan.

This is NOT normal camera-pan activation or electrical/calibration acceptance.
It deliberately uses the existing owned Linux PWM channel for one fixed bare-
servo experiment, without loading settings/.env or changing confirmation flags.
The operator must remain at the physical power disconnect. Initial 1500 us can
cause a LARGE jump from an unknown position, despite the tiny later offsets.
Software cleanup cannot protect against SIGKILL, power loss or blocked hardware.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time
from pathlib import Path
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

CONTROLLER = "32e0000.pwm"
PHYSICAL_PIN = 32
MAX_RUNTIME_S = 4.0
HEALTH_POLL_S = 0.05
HEALTH_TIMEOUT_S = 0.15
HEALTH_BODY_LIMIT = 4096
# At 50 Hz Tegra's 8-bit duty divider has ~78 us steps. Smaller offsets
# (1480/1500/1520 us) can all round to one tick count and never move the servo.
# These remain uncalibrated near-centre commands, not verified physical angles.
PULSE_PLAN = ((1500, 0.7), (1400, 0.4), (1600, 0.4), (1500, 0.5))
WARNING = (
    "EXPERIMENTAL: header power/current and servo signal compatibility are NOT "
    "certified. Jetson may restart. Keep camera removed and bare servo/horn "
    "clear, with a physical power disconnect ready. Initial centering may cause "
    "a LARGE jump. No sweep, retry, autostart or permanent activation is enabled."
)


class CommissioningStopped(RuntimeError):
    """A bounded experiment was interrupted; cleanup must release its channel."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise CommissioningStopped("Refusing a redirected local safety check")


def _local_emergency_stopped():
    """Read only the public, loopback E-stop flag; never auth/status/logs/media."""
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    request = Request(
        "http://127.0.0.1:8765/health", headers={"Accept": "application/json"}
    )
    try:
        with opener.open(request, timeout=HEALTH_TIMEOUT_S) as response:
            if response.status != 200:
                raise CommissioningStopped("Local safety check did not succeed")
            body = response.read(HEALTH_BODY_LIMIT + 1)
        if len(body) > HEALTH_BODY_LIMIT:
            raise CommissioningStopped("Local safety response exceeds its limit")
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise CommissioningStopped("Local safety state is unavailable")
        return payload.get("emergency_stopped")
    except (OSError, ValueError) as exc:
        raise CommissioningStopped("Local safety state is unavailable") from exc


def read_only_plan() -> dict:
    return {
        "read_only": True,
        "physical_header_pin": PHYSICAL_PIN,
        "controller": CONTROLLER,
        "frequency_hz": 50,
        "pulses_us_and_hold_s": PULSE_PLAN,
        "planned_hold_s": sum(duration for _, duration in PULSE_PLAN),
        "watchdog_s": MAX_RUNTIME_S,
        "local_emergency_stop_required": True,
        "configuration_changed": False,
        "warning": WARNING,
    }


def _default_channel(identity: str):
    # Lazy import: a dry run does not import configuration or hardware modules.
    from atlas.hardware.camera_pan_driver import _LinuxPWMChannel

    return _LinuxPWMChannel(identity)


class _SafetyWindow:
    """Linux main-thread alarm plus interrupt cleanup; no child/daemon process."""

    def __init__(self, signal_api):
        self.signals = signal_api
        self.saved = {}

    def __enter__(self):
        api = self.signals
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("Commissioning requires the main thread")
        if api.getitimer(api.ITIMER_REAL)[0] > 0:
            raise RuntimeError("Refusing to replace an existing process alarm")
        try:
            for number in (api.SIGINT, api.SIGTERM, api.SIGALRM):
                self.saved[number] = api.getsignal(number)
                api.signal(number, self._stop)
            api.setitimer(api.ITIMER_REAL, MAX_RUNTIME_S)
        except BaseException:
            self._restore()
            raise
        return self

    @staticmethod
    def _stop(_number, _frame):
        raise CommissioningStopped("Experiment interrupted or watchdog expired")

    def begin_cleanup(self):
        # Do not let a second handled signal interrupt disable/unexport. The
        # operator's physical disconnect remains necessary if cleanup blocks.
        api = self.signals
        api.setitimer(api.ITIMER_REAL, 0)
        for number in self.saved:
            api.signal(number, api.SIG_IGN)

    def _restore(self):
        api = self.signals
        api.setitimer(api.ITIMER_REAL, 0)
        for number, handler in self.saved.items():
            api.signal(number, handler)

    def __exit__(self, *_exception):
        self._restore()


def run_commissioning(
    *,
    execute: bool = False,
    accept_unverified_power: bool = False,
    bare_servo: bool = False,
    channel_factory=None,
    sleep=time.sleep,
    clock=time.monotonic,
    platform: str | None = None,
    signal_api=signal,
    emergency_stopped=None,
) -> dict:
    """Run only the fixed experimental sequence; never modify normal settings.

    Dependency injection exists solely for hardware-free tests. SIGALRM bounds
    normal execution, not blocked cleanup or uncatchable process termination.
    """
    plan = read_only_plan()
    if not execute:
        return plan
    if not accept_unverified_power or not bare_servo:
        raise ValueError("Execution requires power-risk and bare-servo acceptance")
    if (sys.platform if platform is None else platform) != "linux":
        raise RuntimeError("Real commissioning is Linux-only")

    factory = channel_factory or _default_channel
    stop_check = emergency_stopped or _local_emergency_stopped
    channel = None
    started = clock()

    def check_deadline():
        if clock() - started >= MAX_RUNTIME_S:
            raise TimeoutError("Commissioning exceeded its execution window")

    def check_safety():
        check_deadline()
        if stop_check() is not False:
            raise CommissioningStopped("Emergency stop active or safety unknown")
        check_deadline()

    with _SafetyWindow(signal_api) as safety:
        try:
            check_safety()
            channel = factory(CONTROLLER)
            channel.open()  # Existing driver refuses already exported/owned PWM.
            for pulse_us, duration_s in PULSE_PLAN:
                check_safety()
                channel.write_pulse(pulse_us * 1000)
                remaining = duration_s
                while remaining > 1e-9:
                    interval = min(HEALTH_POLL_S, remaining)
                    sleep(interval)
                    remaining -= interval
                    check_safety()
        finally:
            try:
                safety.begin_cleanup()
            finally:
                if channel is not None:
                    # Existing channel disables and unexports only its own PWM.
                    channel.close()

    return {
        **plan,
        "read_only": False,
        "completed": True,
        "output_released": True,
        "electrical_acceptance": False,
        "calibration_confirmed": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--accept-unverified-power", action="store_true")
    parser.add_argument("--bare-servo", action="store_true")
    args = parser.parse_args(argv)
    if args.execute and not (args.accept_unverified_power and args.bare_servo):
        parser.error("--execute requires --accept-unverified-power --bare-servo")
    if args.execute:
        print(WARNING, flush=True)
    try:
        result = run_commissioning(**vars(args))
    except KeyboardInterrupt:
        print("Interrupted; physical power disconnect is required if motion persists.")
        return 130
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            f"Experiment failed ({type(exc).__name__}); no retry. "
            "Disconnect servo power if output cleanup is unconfirmed."
        )
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    raise SystemExit(main())
