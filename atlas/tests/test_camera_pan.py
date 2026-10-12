"""Hardware-free SG90 regression gates, including faults and stale commands."""

from __future__ import annotations

import threading
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from atlas.app.dependency_container import Container
from atlas.config.settings import CameraPanSettings, Settings
from atlas.dashboard.api import create_app
from atlas.hardware.camera_pan import CameraPanController
from atlas.hardware.camera_pan_driver import MockPanDriver, PCA9685PanDriver
from atlas.models.enums import RunMode


class RecordingDriver(MockPanDriver):
    def __init__(self):
        super().__init__()
        self.pulses = []
        self.open_count = 0
        self.disable_count = 0
        self.close_count = 0
        self.failed = False
        self.written = threading.Event()

    def open(self):
        self.open_count += 1

    def write_pulse(self, value):
        if self.failed:
            raise OSError("synthetic bus failure")
        super().write_pulse(value)
        self.pulses.append(value)
        self.written.set()

    def disable(self):
        self.disable_count += 1
        super().disable()

    def close(self):
        self.close_count += 1
        super().close()


@pytest.fixture
def pan():
    driver = RecordingDriver()
    controller = CameraPanController(
        CameraPanSettings(enabled=True),
        driver,
        simulated=True,
        clock=lambda: 10.0,
    )
    controller.start(background=False)
    yield controller, driver
    controller.close()


def command(controller, action, **kwargs):
    return controller.command(
        action,
        client_id=kwargs.pop("client_id", str(uuid4())),
        sequence=kwargs.pop("sequence", 1),
        control_epoch=kwargs.pop("control_epoch", controller.status()["control_epoch"]),
        **kwargs,
    )


@pytest.mark.parametrize(
    "patch",
    [
        {"min_angle": 100, "max_angle": 80},
        {"center_angle": 181},
        {"min_angle": 100},
        {"max_pulse_us": 900},
        {"min_pulse_us": 499},
        {"max_pulse_us": 2501},
        {"sweep_speed_deg_s": float("nan")},
        {"manual_speed_deg_s": float("inf")},
        {"channel": 16},
        {"i2c_address": 0x70},
        {"i2c_bus": -1},
        {"unexpected": True},
    ],
)
def test_invalid_config_fails_before_motion(patch):
    with pytest.raises(ValidationError):
        CameraPanSettings(**patch)


def test_disabled_has_no_motor_or_thread():
    driver = RecordingDriver()
    controller = CameraPanController(CameraPanSettings(), driver, simulated=False)
    controller.start()
    assert controller.status()["mode"] == "disabled"
    assert not driver.open_count and not driver.pulses
    assert controller._thread is None
    with pytest.raises(RuntimeError):
        command(controller, "sweep")
    controller.close()


def test_real_requires_calibration_without_opening_bus():
    driver = RecordingDriver()
    controller = CameraPanController(
        CameraPanSettings(enabled=True),
        driver,
        simulated=False,
    )
    controller.start()
    assert controller.status()["mode"] == "uncalibrated"
    assert not driver.open_count


def test_sweep_reverses_and_repeats_slowly(pan):
    controller, driver = pan
    for _ in range(2000):
        controller.tick(0.05)
    assert min(driver.pulses) == 1000
    assert max(driver.pulses) == 2000
    pairs = list(zip(driver.pulses, driver.pulses[1:], strict=False))
    assert sum(a > b for a, b in pairs) > 700
    assert sum(a < b for a, b in pairs) > 700
    assert max(abs(a - b) for a, b in pairs) <= 1.4
    assert controller.status()["mode"] == "sweep"


def test_scheduler_stall_does_not_jump_to_target(pan):
    controller, _ = pan
    controller.tick(60)
    assert controller.status()["commanded_angle"] == 90.5


def test_manual_position_and_center_stay_speed_limited(pan):
    controller, _ = pan
    command(controller, "position", angle=0)
    controller.tick(0.1)
    assert controller.status()["commanded_angle"] == 88.5
    for _ in range(100):
        controller.tick(0.1)
    assert controller.status()["commanded_angle"] == 0
    assert controller.status()["mode"] == "hold"
    command(controller, "center")
    for _ in range(60):
        controller.tick(0.1)
    assert controller.status()["commanded_angle"] == 90
    command(controller, "sweep")
    assert controller.status()["mode"] == "sweep"


@pytest.mark.parametrize("angle", [-1, 181, float("nan"), float("inf"), None])
def test_invalid_target_does_not_change_existing_motion(pan, angle):
    controller, driver = pan
    before = controller.status()
    with pytest.raises(ValueError):
        command(controller, "position", angle=angle)
    assert controller.status() == before
    assert len(driver.pulses) == 1


def test_custom_calibration_limits_apply_to_every_mode():
    cfg = CameraPanSettings(
        enabled=True, min_angle=20, max_angle=140, min_pulse_us=1100, max_pulse_us=1900
    )
    driver = RecordingDriver()
    controller = CameraPanController(cfg, driver, simulated=True, clock=lambda: 0)
    controller.start(background=False)
    for _ in range(1000):
        controller.tick(0.1)
    with pytest.raises(ValueError):
        command(controller, "position", angle=180)
    command(controller, "jog", direction=-1)
    for _ in range(100):
        controller.tick(0.1, now=0.1)
    assert controller.status()["commanded_angle"] == 20
    assert min(driver.pulses) >= 1100 and max(driver.pulses) <= 1900
    controller.close()


def test_disconnect_jog_lease_stops_without_resuming_sweep(pan):
    controller, driver = pan
    command(controller, "jog", direction=-1)
    controller.tick(0.1, now=10.2)
    assert controller.status()["commanded_angle"] == 88.5
    controller.tick(0.1, now=10.6)
    pulses = list(driver.pulses)
    controller.tick(0.1, now=100)
    assert controller.status()["mode"] == "hold"
    assert driver.pulses == pulses


def test_late_jog_cannot_restart_after_release(pan):
    controller, _ = pan
    owner = str(uuid4())
    command(controller, "jog", direction=1, client_id=owner, sequence=1)
    command(controller, "hold", client_id=owner, sequence=3)
    with pytest.raises(ValueError, match="Stale"):
        command(controller, "jog", direction=1, client_id=owner, sequence=2)
    assert controller.status()["mode"] == "hold"


def test_emergency_stop_disables_and_invalidates_old_commands(pan):
    controller, driver = pan
    old_epoch = controller.status()["control_epoch"]
    controller.emergency_stop()
    assert driver.pulse_us is None
    before = list(driver.pulses)
    controller.tick(0.1)
    with pytest.raises(RuntimeError):
        command(controller, "sweep")
    controller.clear_emergency_stop()
    assert controller.status()["mode"] == "hold"
    controller.tick(0.1)
    assert driver.pulses == before
    with pytest.raises(RuntimeError, match="state changed"):
        command(controller, "sweep", control_epoch=old_epoch)
    command(controller, "sweep")
    controller.tick(0.1)
    assert driver.pulse_us is not None


def test_separate_exhibit_emergency_guard_stops_pan():
    stopped = [False]
    driver = RecordingDriver()
    controller = CameraPanController(
        CameraPanSettings(enabled=True),
        driver,
        simulated=True,
        emergency_guard=lambda: stopped[0],
    )
    controller.start(background=False)
    stopped[0] = True
    controller.tick(0.1)
    assert controller.status()["emergency_stopped"]
    assert driver.pulse_us is None
    controller.close()


def test_fault_stops_and_does_not_auto_retry(pan):
    controller, driver = pan
    driver.failed = True
    controller.tick(0.1)
    assert controller.status()["mode"] == "fault"
    assert not controller.status()["ready"]
    assert driver.close_count == 1 and driver.pulse_us is None
    controller.start()
    assert driver.open_count == 1
    with pytest.raises(RuntimeError):
        command(controller, "center")


def test_disable_failure_reports_cut_power(pan, monkeypatch):
    controller, driver = pan

    def fail():
        raise OSError("synthetic")

    monkeypatch.setattr(driver, "disable", fail)
    controller.emergency_stop()
    assert controller.status()["mode"] == "fault"
    assert "cut servo power" in controller.status()["detail"]


def test_background_start_is_idempotent_and_close_joins():
    driver = RecordingDriver()
    controller = CameraPanController(
        CameraPanSettings(enabled=True), driver, simulated=True
    )
    controller.start()
    first_thread = controller._thread
    driver.written.clear()
    controller.start()
    assert driver.written.wait(1)
    controller.close()
    assert driver.open_count == 1
    assert controller._thread is first_thread and not first_thread.is_alive()
    assert driver.pulse_us is None


class FakeBus:
    def __init__(self):
        self.registers = {}
        self.writes = []
        self.closed = False

    def read_byte_data(self, addr, register):
        return self.registers.get(register, 0)

    def write_byte_data(self, addr, register, value):
        self.writes.append((addr, register, [value]))
        self.registers[register] = value

    def write_i2c_block_data(self, addr, register, values):
        self.writes.append((addr, register, values))
        self.registers.update({register + i: value for i, value in enumerate(values)})

    def close(self):
        self.closed = True


def test_pca_registers_frequency_duty_and_channel_only_shutdown():
    bus = FakeBus()
    cfg = CameraPanSettings(i2c_bus=7, channel=3)
    driver = PCA9685PanDriver(cfg, bus_factory=lambda number: bus)
    driver.open()
    assert bus.registers[0xFE] == 121
    driver.write_pulse(1500)
    assert bus.writes[-1] == (0x40, 18, [0, 0, 51, 1])
    size = len(bus.writes)
    driver.write_pulse(1500)
    assert len(bus.writes) == size
    with pytest.raises(ValueError):
        driver.write_pulse(2500)
    driver.disable()
    assert bus.writes[-1] == (0x40, 21, [16])
    assert not any(
        register in range(0xFA, 0xFE) or addr == 0 for addr, register, _ in bus.writes
    )
    driver.close()
    assert bus.closed


@pytest.mark.parametrize(
    "register,value", [(0x00, 0x40), (0xFB, 0x10), (0xFD, 0x10), (0x0A + 2, 100)]
)
def test_pca_refuses_external_clock_global_off_or_active_shared_board(register, value):
    bus = FakeBus()
    bus.registers[register] = value
    driver = PCA9685PanDriver(CameraPanSettings(i2c_bus=7), bus_factory=lambda _: bus)
    with pytest.raises(RuntimeError):
        driver.open()
    assert not bus.writes
    assert bus.closed


def test_no_bus_selected_fails_without_importing_hardware():
    driver = PCA9685PanDriver(CameraPanSettings())
    with pytest.raises(RuntimeError, match="not configured"):
        driver.open()


@pytest.fixture
def api_pan(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_ADMIN_TOKEN", "pan-test-token")
    cfg = Settings(camera_pan=CameraPanSettings(enabled=True))
    cfg.paths.logs_dir = tmp_path / "logs"
    cfg.paths.sqlite_dir = tmp_path / "sqlite"
    container = Container(cfg)
    headers = {"X-Atlas-Admin-Token": "pan-test-token"}
    with TestClient(create_app(container)) as client:
        yield client, container, headers


def payload(container, default_action="hold", **kwargs):
    return {
        "action": default_action,
        "client_id": str(uuid4()),
        "sequence": 1,
        "control_epoch": container.camera_pan.status()["control_epoch"],
        **kwargs,
    }


def test_admin_pan_routes_require_auth(api_pan):
    client, container, _ = api_pan
    assert client.get("/api/admin/arducam/pan/status").status_code == 401
    before = container.camera_pan.status()["mode"]
    assert (
        client.post(
            "/api/admin/arducam/pan/control", json=payload(container)
        ).status_code
        == 401
    )
    assert container.camera_pan.status()["mode"] == before


def test_status_and_all_commands_are_mock_lifecycle_owned(api_pan):
    client, container, headers = api_pan
    response = client.get("/api/admin/arducam/pan/status", headers=headers)
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["simulated"] and response.json()["mode"] == "sweep"
    for action, extra in [
        ("jog", {"direction": -1}),
        ("hold", {}),
        ("position", {"angle": 42}),
        ("center", {}),
        ("sweep", {}),
    ]:
        response = client.post(
            "/api/admin/arducam/pan/control",
            headers=headers,
            json=payload(container, action, **extra),
        )
        assert response.status_code == 200
    assert container._arducam_source is None
    assert container._tts is None and container._dialogue_engine is None


@pytest.mark.parametrize(
    "patch",
    [
        {"action": "follow"},
        {"action": "position"},
        {"action": "position", "angle": 181},
        {"action": "jog", "direction": 0},
        {"action": "jog", "direction": True},
        {"sequence": True},
        {"client_id": "bad"},
        {"sequence": -1},
        {"angle": 50},
        {"extra": "bad"},
    ],
)
def test_rejected_api_requests_do_not_override_sweep(api_pan, patch):
    client, container, headers = api_pan
    response = client.post(
        "/api/admin/arducam/pan/control",
        headers=headers,
        json=payload(container, "sweep", **patch),
    )
    assert response.status_code == 422
    assert container.camera_pan.status()["mode"] == "sweep"


def test_api_emergency_stop_clear_and_delayed_packet(api_pan):
    client, container, headers = api_pan
    old = payload(container, "sweep")
    assert client.post("/hardware/emergency-stop").status_code == 200
    assert container.camera_pan.status()["emergency_stopped"]
    assert (
        client.post(
            "/api/admin/arducam/pan/control", headers=headers, json=old
        ).status_code
        == 409
    )
    response = client.post("/hardware/clear-emergency-stop", headers=headers)
    assert response.status_code == 200
    assert container.camera_pan.status()["mode"] == "hold"
    assert (
        client.post(
            "/api/admin/arducam/pan/control", headers=headers, json=old
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/admin/arducam/pan/control",
            headers=headers,
            json=payload(container, "sweep"),
        ).status_code
        == 200
    )


def test_standalone_shutdown_and_device_dashboard_ownership(tmp_path):
    container = Container(Settings(camera_pan=CameraPanSettings(enabled=True)))
    with TestClient(create_app(container, manage_camera_pan=False)):
        assert container._camera_pan is None
    with TestClient(create_app(container)):
        assert container.camera_pan.status()["ready"]
    assert container.camera_pan.status()["mode"] == "stopped"
    assert not container.camera_pan._thread.is_alive()


def test_device_default_disabled_and_opt_in_missing_board_are_nonfatal(tmp_path):
    container = Container(Settings(mode=RunMode.DEVICE))
    container.start_camera_pan()
    assert container._camera_pan is None
    assert container.camera_pan.status()["mode"] == "disabled"
    container.close()
    container = Container(
        Settings(
            mode=RunMode.DEVICE,
            camera_pan=CameraPanSettings(
                enabled=True,
                calibration_confirmed=True,
            ),
        )
    )
    container.start_camera_pan()
    assert container.camera_pan.status()["mode"] == "fault"
    assert container._tts is None and container._dialogue_engine is None
    container.close()


def test_visitor_page_has_no_motor_controls(api_pan):
    client, _, _ = api_pan
    visitor = client.get("/").text
    assert 'id="pan-left"' not in visitor
    assert "/api/admin/arducam/pan" not in visitor
    assert 'id="pan-left"' in client.get("/admin").text
