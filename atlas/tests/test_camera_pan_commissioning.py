"""Hardware-free tests for the explicit, temporary bare-servo experiment."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "commission_camera_pan.py"
SPEC = importlib.util.spec_from_file_location("commission_camera_pan", SCRIPT)
commission = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(commission)


class FakeSignals:
    SIGINT, SIGTERM, SIGALRM, SIG_IGN, ITIMER_REAL = 2, 15, 14, 1, 0

    def __init__(self):
        self.handlers = {number: object() for number in (2, 15, 14)}
        self.original = dict(self.handlers)
        self.timers = []
        self.existing_alarm = 0

    def getsignal(self, number):
        return self.handlers[number]

    def signal(self, number, handler):
        self.handlers[number] = handler

    def getitimer(self, _timer):
        return self.existing_alarm, 0

    def setitimer(self, timer, duration):
        self.timers.append((timer, duration))


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, duration):
        self.sleeps.append(duration)
        self.now += duration


class FakeChannel:
    def __init__(self):
        self.open_count = 0
        self.close_count = 0
        self.pulses = []
        self.open_error = None
        self.write_error = None

    def open(self):
        self.open_count += 1
        if self.open_error:
            raise self.open_error

    def write_pulse(self, value):
        self.pulses.append(value)
        if self.write_error:
            raise self.write_error

    def close(self):
        self.close_count += 1


def execute(channel=None, signals=None, timer=None, **kwargs):
    channel = channel or FakeChannel()
    signals = signals or FakeSignals()
    timer = timer or FakeClock()
    identities = []

    def factory(identity):
        identities.append(identity)
        return channel

    result = commission.run_commissioning(
        execute=True,
        accept_unverified_power=True,
        bare_servo=True,
        channel_factory=factory,
        sleep=kwargs.pop("sleep", timer.sleep),
        clock=timer,
        platform="linux",
        signal_api=signals,
        emergency_stopped=kwargs.pop("emergency_stopped", lambda: False),
        **kwargs,
    )
    return result, identities


@pytest.mark.parametrize("platform", ["linux", "win32", "darwin"])
def test_default_is_read_only_without_constructing_hardware(platform):
    def forbidden(_identity):
        pytest.fail("A dry run must not construct hardware")

    result = commission.run_commissioning(
        channel_factory=forbidden,
        platform=platform,
        signal_api=object(),
        emergency_stopped=lambda: pytest.fail("Dry run must not query health"),
    )
    assert result["read_only"] is True
    assert result["configuration_changed"] is False
    assert result["physical_header_pin"] == 32
    assert result["controller"] == "32e0000.pwm"
    assert "LARGE jump" in result["warning"]


@pytest.mark.parametrize("power,bare", [(False, False), (False, True), (True, False)])
def test_missing_acceptance_never_constructs_hardware(power, bare):
    def forbidden(_identity):
        pytest.fail("Missing acceptance must not construct hardware")

    with pytest.raises(ValueError):
        commission.run_commissioning(
            execute=True,
            accept_unverified_power=power,
            bare_servo=bare,
            channel_factory=forbidden,
            platform="linux",
        )


@pytest.mark.parametrize("platform", ["win32", "darwin"])
def test_execution_refuses_non_linux_before_hardware(platform):
    with pytest.raises(RuntimeError, match="Linux-only"):
        commission.run_commissioning(
            execute=True,
            accept_unverified_power=True,
            bare_servo=True,
            platform=platform,
            signal_api=object(),
        )


def test_exact_short_sequence_and_normal_cleanup():
    channel, signals, timer = FakeChannel(), FakeSignals(), FakeClock()
    result, identities = execute(channel, signals, timer)
    assert identities == ["32e0000.pwm"]
    assert channel.pulses == [1_500_000, 1_400_000, 1_600_000, 1_500_000]
    assert sum(timer.sleeps) == pytest.approx(2.0)
    assert max(timer.sleeps) <= 0.05
    assert timer.now == pytest.approx(2.0)
    assert channel.open_count == channel.close_count == 1
    assert signals.timers[0] == (0, 4.0)
    assert signals.timers[-1] == (0, 0)
    assert signals.handlers == signals.original
    assert result["completed"] and result["output_released"]
    assert not result["electrical_acceptance"]
    assert not result["calibration_confirmed"]
    assert not result["configuration_changed"]


def test_small_wiggle_uses_distinct_tegra_duty_steps_without_sweeping():
    period_us = 20_000
    ticks = [
        (pulse_us * 256 + period_us // 2) // period_us
        for pulse_us, _duration in commission.PULSE_PLAN
    ]
    assert ticks == [19, 18, 20, 19]
    assert all(1400 <= pulse <= 1600 for pulse, _ in commission.PULSE_PLAN)


@pytest.mark.parametrize("stage", ["open", "write"])
def test_failure_closes_even_partially_open_channel(stage):
    channel, signals = FakeChannel(), FakeSignals()
    setattr(channel, f"{stage}_error", OSError("synthetic failure"))
    with pytest.raises(OSError):
        execute(channel, signals)
    assert channel.close_count == 1
    assert signals.handlers == signals.original
    assert signals.timers[-1] == (0, 0)


@pytest.mark.parametrize("error", [KeyboardInterrupt(), OSError("synthetic")])
def test_sleep_failure_releases_output(error):
    channel, signals = FakeChannel(), FakeSignals()

    def interrupted(_duration):
        raise error

    with pytest.raises(type(error)):
        execute(channel, signals, sleep=interrupted)
    assert channel.close_count == 1
    assert len(channel.pulses) == 1
    assert signals.handlers == signals.original


@pytest.mark.parametrize("number", [2, 15, 14])
def test_handled_interrupt_or_watchdog_releases_output(number):
    channel, signals = FakeChannel(), FakeSignals()

    def interrupted(_duration):
        signals.handlers[number](number, None)

    with pytest.raises(commission.CommissioningStopped):
        execute(channel, signals, sleep=interrupted)
    assert channel.close_count == 1
    assert len(channel.pulses) == 1
    assert signals.handlers == signals.original


def test_elapsed_deadline_stops_before_another_pulse():
    channel, signals, timer = FakeChannel(), FakeSignals(), FakeClock()

    def delayed(_duration):
        timer.now += 4.1

    with pytest.raises(TimeoutError):
        execute(channel, signals, timer, sleep=delayed)
    assert channel.pulses == [1_500_000]
    assert channel.close_count == 1
    assert signals.handlers == signals.original


def test_existing_alarm_refused_without_hardware():
    signals = FakeSignals()
    signals.existing_alarm = 0.5
    channel = FakeChannel()
    with pytest.raises(RuntimeError, match="existing process alarm"):
        execute(channel, signals)
    assert channel.open_count == 0
    assert signals.handlers == signals.original
    assert not signals.timers


def test_constructor_failure_restores_handlers_and_alarm():
    signals = FakeSignals()

    def failed(_identity):
        raise OSError("synthetic constructor failure")

    with pytest.raises(OSError):
        commission.run_commissioning(
            execute=True,
            accept_unverified_power=True,
            bare_servo=True,
            channel_factory=failed,
            platform="linux",
            signal_api=signals,
            emergency_stopped=lambda: False,
        )
    assert signals.handlers == signals.original
    assert signals.timers[-1] == (0, 0)


def test_cli_defaults_to_plan_and_rejects_custom_pulses(capsys):
    assert commission.main([]) == 0
    assert '"read_only": true' in capsys.readouterr().out
    with pytest.raises(SystemExit):
        commission.main(["--pulse-us", "2500"])


def test_cli_requires_both_acknowledgements_before_execute():
    with pytest.raises(SystemExit):
        commission.main(["--execute"])


@pytest.mark.parametrize("state", [True, None, "false", 0, {}, []])
def test_stop_or_unknown_state_prevents_hardware_construction(state):
    channel = FakeChannel()
    with pytest.raises(commission.CommissioningStopped):
        execute(channel, emergency_stopped=lambda: state)
    assert channel.open_count == channel.close_count == 0
    assert not channel.pulses


def test_unreachable_safety_prevents_open():
    channel = FakeChannel()

    def unavailable():
        raise OSError("synthetic unavailable health")

    with pytest.raises(OSError):
        execute(channel, emergency_stopped=unavailable)
    assert not channel.open_count and not channel.pulses


def test_emergency_stop_during_hold_releases_output():
    channel = FakeChannel()
    states = iter([False, False, True])
    with pytest.raises(commission.CommissioningStopped):
        execute(channel, emergency_stopped=lambda: next(states))
    assert channel.pulses == [1_500_000]
    assert channel.close_count == 1


def test_health_failure_during_hold_releases_output():
    channel = FakeChannel()
    calls = 0

    def fails_after_start():
        nonlocal calls
        calls += 1
        if calls > 2:
            raise OSError("synthetic unavailable health")
        return False

    with pytest.raises(OSError):
        execute(channel, emergency_stopped=fails_after_start)
    assert channel.pulses == [1_500_000]
    assert channel.close_count == 1


@pytest.mark.parametrize(
    "body,status,error",
    [
        (b'{"emergency_stopped":false}', 200, None),
        (b'{"emergency_stopped":true}', 200, None),
        (b"{}", 200, None),
        (b"not json", 200, commission.CommissioningStopped),
        (b"[]", 200, commission.CommissioningStopped),
        (b"x" * 4097, 200, commission.CommissioningStopped),
        (b"{}", 503, commission.CommissioningStopped),
    ],
)
def test_local_health_is_bounded_loopback_only(monkeypatch, body, status, error):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def read(self, maximum):
            assert maximum == 4097
            return body

    response = Response()
    response.status = status

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "http://127.0.0.1:8765/health"
            assert timeout == 0.15
            assert not request.has_header("Authorization")
            assert not request.has_header("X-Atlas-Admin-Token")
            return response

    def build(proxy, no_redirect):
        assert proxy.proxies == {}
        assert isinstance(no_redirect, commission._NoRedirect)
        return Opener()

    monkeypatch.setattr(commission, "build_opener", build)
    if error:
        with pytest.raises(error):
            commission._local_emergency_stopped()
    else:
        assert commission._local_emergency_stopped() is {
            b'{"emergency_stopped":false}': False,
            b'{"emergency_stopped":true}': True,
            b"{}": None,
        }[body]


def test_local_health_refuses_redirect():
    with pytest.raises(commission.CommissioningStopped):
        commission._NoRedirect().redirect_request(None, None, None, None, None, None)


def test_never_loads_or_constructs_normal_settings(monkeypatch):
    from atlas.config import settings

    def forbidden(*_args, **_kwargs):
        pytest.fail("Commissioning must not load/construct normal settings")

    monkeypatch.setattr(settings, "Settings", forbidden)
    monkeypatch.setattr(settings, "CameraPanSettings", forbidden)
    result, _ = execute()
    assert not result["configuration_changed"]
