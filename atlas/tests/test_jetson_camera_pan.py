"""Direct PWM tests: synthetic kernel files/channel only, never a real Jetson."""

import errno
from pathlib import Path

import pytest
from pydantic import ValidationError

from atlas.app.dependency_container import Container
from atlas.config.settings import CameraPanSettings, Settings
from atlas.hardware import camera_pan_driver
from atlas.hardware.camera_pan import CameraPanController
from atlas.hardware.camera_pan_driver import (
    JETSON_HEADER_PWM,
    JetsonPWMPanDriver,
    MockPanDriver,
    _LinuxPWMChannel,
)
from atlas.models.enums import RunMode


def direct_settings(**patch):
    return CameraPanSettings(
        **{
            "driver": "jetson_pwm",
            "enabled": True,
            "calibration_confirmed": True,
            "pinmux_confirmed": True,
            "power_confirmed": True,
            **patch,
        }
    )


class FakeChannel:
    def __init__(self):
        self.opened = self.disabled = self.closed = 0
        self.pulses = []
        self.fail_write = False

    def open(self):
        self.opened += 1

    def write_pulse(self, pulse):
        if self.fail_write:
            raise PermissionError("synthetic failure")
        self.pulses.append(pulse)

    def disable(self):
        self.disabled += 1

    def close(self):
        self.closed += 1


class Ownership:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


@pytest.mark.parametrize("pin,identity", [(15, "3280000.pwm"), (32, "32e0000.pwm")])
def test_direct_waveform_routing_conversion_repeat_disable_and_rearm(pin, identity):
    channel = FakeChannel()
    received = []
    driver = JetsonPWMPanDriver(
        direct_settings(jetson_board_pin=pin),
        channel_factory=lambda name: received.append(name) or channel,
    )
    driver.open()
    driver.open()
    driver.write_pulse(1500)
    driver.write_pulse(1500)
    assert channel.pulses == [1_500_000]
    assert received == [identity] and channel.opened == 1
    driver.disable()
    driver.write_pulse(1500)
    assert channel.pulses == [1_500_000, 1_500_000]
    driver.close()
    driver.close()
    assert channel.closed == 1
    with pytest.raises(RuntimeError):
        driver.write_pulse(1500)


@pytest.mark.parametrize("pulse", [0, 999, 2001, float("nan"), float("inf")])
def test_direct_invalid_pulses_never_reach_kernel(pulse):
    channel = FakeChannel()
    driver = JetsonPWMPanDriver(direct_settings(), channel_factory=lambda _: channel)
    driver.open()
    with pytest.raises(ValueError):
        driver.write_pulse(pulse)
    assert not channel.pulses
    driver.close()


@pytest.mark.parametrize("missing", ["pinmux_confirmed", "power_confirmed"])
def test_unverified_setup_never_opens_or_exports(missing):
    settings = direct_settings(**{missing: False})
    channel = FakeChannel()
    driver = JetsonPWMPanDriver(settings, channel_factory=lambda _: channel)
    controller = CameraPanController(settings, driver, simulated=False)
    controller.start(background=False)
    assert controller.status()["mode"] == "setup_required"
    assert not channel.opened and not channel.pulses
    with pytest.raises(RuntimeError):
        driver.open()
    controller.close()


@pytest.mark.parametrize(
    "patch",
    [
        {"jetson_board_pin": 33},
        {"jetson_board_pin": 12},
        {"driver": "software_pwm"},
        {"startup_mode": "unknown"},
    ],
)
def test_unsupported_pin_driver_or_mode_rejected(patch):
    with pytest.raises(ValidationError):
        direct_settings(**patch)


def test_direct_kernel_failure_is_optional_and_never_reconnects():
    settings = direct_settings()
    channel = FakeChannel()
    driver = JetsonPWMPanDriver(settings, channel_factory=lambda _: channel)
    controller = CameraPanController(settings, driver, simulated=False)
    controller.start(background=False)
    channel.fail_write = True
    controller.tick(0.05)
    assert controller.status()["mode"] == "fault"
    assert channel.closed == 1 and channel.disabled == 1
    controller.start()
    assert channel.opened == 1
    controller.close()


def test_real_startup_hold_and_emergency_stop_do_not_resume():
    settings = direct_settings(startup_mode="hold")
    channel = FakeChannel()
    controller = CameraPanController(
        settings,
        JetsonPWMPanDriver(settings, channel_factory=lambda _: channel),
        simulated=False,
    )
    controller.start(background=False)
    for _ in range(100):
        controller.tick(0.1)
    assert channel.pulses == [1_500_000]
    assert controller.status()["mode"] == "hold"
    controller.emergency_stop()
    controller.clear_emergency_stop()
    controller.tick(0.1)
    assert channel.pulses == [1_500_000] and channel.disabled == 1
    controller.close()


def test_demo_direct_config_uses_mock_and_default_device_is_nonmoving():
    container = Container(Settings(mode=RunMode.DEMO, camera_pan=direct_settings()))
    assert isinstance(container.camera_pan.driver, MockPanDriver)
    assert container.camera_pan.status()["simulated"]
    assert "physical pin 32" in container.camera_pan.status()["connection"]
    container.close()
    container = Container(Settings(mode=RunMode.DEVICE))
    container.start_camera_pan()
    assert container._camera_pan is None
    container.close()


def make_kernel(
    tmp_path,
    monkeypatch,
    *,
    preexported=False,
    fail_write=None,
    polarity="normal",
    initial_state=None,
    reject_zero_period_apply=False,
):
    root = tmp_path / "class" / "pwm"
    chip = root / "pwmchip42"
    device = tmp_path / "devices" / JETSON_HEADER_PWM[32]
    device.mkdir(parents=True)
    chip.mkdir(parents=True)
    # Windows symlinks need privileges; substitute only Path.resolve for the
    # synthetic device link. Production still resolves actual kernel symlinks.
    original_resolve = Path.resolve
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda self, *a, **k: (
            device if self == chip / "device" else original_resolve(self, *a, **k)
        ),
    )
    (chip / "npwm").write_text("1")
    writes = []
    original_write = Path.write_text

    def write(self, value, **kwargs):
        writes.append((self.name, value))
        if fail_write == self.name:
            raise PermissionError("synthetic permission failure")
        if (
            reject_zero_period_apply
            and self.parent == chip / "pwm0"
            and self.name in ("enable", "duty_cycle")
            and (chip / "pwm0" / "period").read_text() == "0"
        ):
            raise OSError(errno.EINVAL, "synthetic PWM apply rejects zero period")
        if self == chip / "export":
            (chip / "pwm0").mkdir()
            state = {"enable": "0", "duty_cycle": "0", "period": "0"}
            state.update(initial_state or {})
            for name, initial in state.items():
                original_write(chip / "pwm0" / name, initial)
            if polarity is not None:
                original_write(chip / "pwm0" / "polarity", polarity)
        return original_write(self, value, **kwargs)

    monkeypatch.setattr(Path, "write_text", write)
    if preexported:
        (chip / "pwm0").mkdir()
    ownership = Ownership()
    channel = _LinuxPWMChannel(
        JETSON_HEADER_PWM[32],
        sysfs_root=root,
        ownership_factory=lambda _: ownership,
    )
    return channel, chip, ownership, writes


def test_kernel_chip_identity_not_numeric_index_and_only_owned_shutdown(
    tmp_path, monkeypatch
):
    channel, chip, ownership, writes = make_kernel(tmp_path, monkeypatch)
    channel.open()
    channel.write_pulse(1_500_000)
    assert (chip / "pwm0" / "period").read_text() == "20000000"
    assert (chip / "pwm0" / "enable").read_text() == "1"
    channel.disable()
    assert writes[-2:] == [("duty_cycle", "0"), ("enable", "0")]
    channel.close()
    assert writes[-1] == ("unexport", "0") and ownership.closed


def test_kernel_initializes_zero_period_before_any_state_apply(tmp_path, monkeypatch):
    channel, chip, ownership, writes = make_kernel(
        tmp_path, monkeypatch, reject_zero_period_apply=True
    )
    channel.open()
    assert writes == [
        ("export", "0"),
        ("period", "20000000"),
        ("enable", "0"),
        ("duty_cycle", "0"),
    ]
    assert (chip / "pwm0" / "enable").read_text() == "0"
    assert (chip / "pwm0" / "duty_cycle").read_text() == "0"
    channel.close()
    assert writes[-1] == ("unexport", "0") and ownership.closed


@pytest.mark.parametrize(
    "initial_state",
    [
        {"enable": "1"},
        {"enable": "unknown"},
        {"duty_cycle": "1000"},
        {"duty_cycle": "-1"},
        {"duty_cycle": "unknown"},
    ],
)
def test_kernel_unexpected_initial_state_never_sets_period_or_enables(
    tmp_path, monkeypatch, initial_state
):
    channel, _, ownership, writes = make_kernel(
        tmp_path,
        monkeypatch,
        initial_state={"period": "20000000", **initial_state},
        reject_zero_period_apply=True,
    )
    with pytest.raises(RuntimeError, match="disabled with zero duty"):
        channel.open()
    assert not any(name == "period" for name, _ in writes)
    assert not any(
        name in ("enable", "duty_cycle") and value != "0" for name, value in writes
    )
    assert writes[-1] == ("unexport", "0") and ownership.closed


def test_kernel_already_exported_pwm_is_untouched_even_if_disabled(
    tmp_path, monkeypatch
):
    channel, _, ownership, writes = make_kernel(tmp_path, monkeypatch, preexported=True)
    with pytest.raises(RuntimeError, match="already exported"):
        channel.open()
    assert not writes and ownership.closed
    channel.close()
    assert not writes


def test_kernel_missing_controller_and_fan_are_never_touched(tmp_path):
    with pytest.raises(ValueError):
        _LinuxPWMChannel("pwm-fan")
    channel = _LinuxPWMChannel("32e0000.pwm", sysfs_root=tmp_path)
    with pytest.raises(RuntimeError, match="unavailable"):
        channel.open()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("failure", ["export", "period"])
def test_kernel_setup_failure_releases_only_its_export(tmp_path, monkeypatch, failure):
    channel, _, ownership, writes = make_kernel(
        tmp_path, monkeypatch, fail_write=failure
    )
    with pytest.raises(PermissionError):
        channel.open()
    assert ownership.closed
    assert (("unexport", "0") in writes) == (failure != "export")


def test_kernel_normal_read_only_polarity_is_never_written(tmp_path, monkeypatch):
    channel, _, ownership, writes = make_kernel(
        tmp_path, monkeypatch, fail_write="polarity", polarity="normal\n"
    )
    channel.open()
    channel.write_pulse(1_500_000)
    channel.close()
    assert not any(name == "polarity" for name, _ in writes)
    assert ("enable", "1") in writes
    assert writes[-1] == ("unexport", "0") and ownership.closed


@pytest.mark.parametrize("polarity", ["inversed", "unknown", "0", "", None])
def test_kernel_wrong_or_missing_polarity_never_enables(
    tmp_path, monkeypatch, polarity
):
    channel, _, ownership, writes = make_kernel(
        tmp_path, monkeypatch, polarity=polarity
    )
    expected = FileNotFoundError if polarity is None else RuntimeError
    with pytest.raises(expected):
        channel.open()
    assert not any(
        name in ("enable", "duty_cycle") and value != "0" for name, value in writes
    )
    assert not any(name == "polarity" for name, _ in writes)
    assert writes[-1] == ("unexport", "0") and ownership.closed


def test_kernel_waits_for_existing_udev_write_permissions(tmp_path, monkeypatch):
    channel, _, ownership, writes = make_kernel(tmp_path, monkeypatch)
    now, sleeps, checked = [0.0], [], []

    def access(path, mode):
        assert mode == camera_pan_driver.os.W_OK
        checked.append(path.name)
        return now[0] >= 0.03

    def sleep(duration):
        assert writes == [("export", "0")]
        sleeps.append(duration)
        now[0] += duration

    monkeypatch.setattr(camera_pan_driver.os, "access", access)
    monkeypatch.setattr(camera_pan_driver.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(camera_pan_driver.time, "sleep", sleep)
    channel.open()
    assert sleeps == [0.01, 0.01, 0.01]
    assert set(checked) == {"enable", "duty_cycle", "period"}
    assert ("period", "20000000") in writes
    channel.close()
    assert writes[-1] == ("unexport", "0") and ownership.closed


def test_kernel_udev_permission_timeout_releases_owned_export(tmp_path, monkeypatch):
    channel, _, ownership, writes = make_kernel(tmp_path, monkeypatch)
    now, sleeps = [0.0], []

    def sleep(duration):
        assert writes == [("export", "0")]
        sleeps.append(duration)
        now[0] += duration

    monkeypatch.setattr(camera_pan_driver.os, "access", lambda *_args: False)
    monkeypatch.setattr(camera_pan_driver.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(camera_pan_driver.time, "sleep", sleep)
    with pytest.raises(RuntimeError, match="writable attributes"):
        channel.open()
    assert sum(sleeps) == pytest.approx(1.0)
    assert now[0] <= 1.0
    assert not any(
        name in ("enable", "duty_cycle") and value != "0" for name, value in writes
    )
    assert writes[-1] == ("unexport", "0") and ownership.closed


def test_kernel_lock_failure_does_not_export(tmp_path, monkeypatch):
    channel, _, _, writes = make_kernel(tmp_path, monkeypatch)

    def reject(_):
        raise RuntimeError("owned")

    channel._ownership_factory = reject
    with pytest.raises(RuntimeError, match="owned"):
        channel.open()
    assert not writes


def test_thread_start_failure_does_not_break_other_resource_cleanup(monkeypatch):
    import threading

    def fail(_):
        raise RuntimeError("Synthetic thread unavailable")

    monkeypatch.setattr(threading.Thread, "start", fail)
    controller = CameraPanController(
        direct_settings(),
        MockPanDriver(),
        simulated=True,
    )
    controller.start()
    assert controller.status()["mode"] == "fault"
    controller.close()  # Must not join an unstarted thread.


def test_preflight_is_read_only_and_does_not_claim_or_load_settings(
    tmp_path, monkeypatch
):
    import importlib.util

    script = Path(__file__).parents[1] / "scripts" / "check_camera_pan_pwm.py"
    spec = importlib.util.spec_from_file_location("pan_preflight", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _, chip, ownership, writes = make_kernel(tmp_path, monkeypatch)
    report = module.inspect_pwm(chip.parent)
    assert report["read_only"]
    assert report["candidates"][1]["found"]
    assert report["candidates"][1]["physical_header_pin"] == 32
    assert not writes and not ownership.closed
