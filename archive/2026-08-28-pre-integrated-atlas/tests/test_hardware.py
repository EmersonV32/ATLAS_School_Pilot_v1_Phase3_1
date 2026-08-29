"""Tests for the hardware safety layer (emergency stop)."""
from __future__ import annotations

from atlas.hardware.base import StandCommand
from atlas.hardware.mock_hardware import MockHardware


class RecordingHardware(MockHardware):
    def __init__(self) -> None:
        self.sent: list[StandCommand] = []
        self.leds: list[str] = []

    def _send_command(self, command: StandCommand, stand_id: int = 1) -> None:
        self.sent.append(command)

    def set_status_led(self, colour: str) -> None:
        self.leds.append(colour)


class TestEmergencyStop:
    def test_movement_blocked_while_stopped(self):
        hw = RecordingHardware()
        hw.emergency_stop()
        hw.send(StandCommand.ROTATE_CW)
        hw.send(StandCommand.ROTATE_CCW)
        assert hw.sent == []
        assert hw.emergency_stopped is True

    def test_movement_resumes_after_clear(self):
        hw = RecordingHardware()
        hw.emergency_stop()
        hw.clear_emergency_stop()
        hw.send(StandCommand.ROTATE_CW)
        assert hw.sent == [StandCommand.ROTATE_CW]
        assert hw.emergency_stopped is False

    def test_stop_sets_red_led(self):
        hw = RecordingHardware()
        hw.emergency_stop()
        assert "red" in hw.leds

    def test_normal_send_works(self):
        hw = RecordingHardware()
        hw.send(StandCommand.CENTER)
        assert hw.sent == [StandCommand.CENTER]

    def test_estop_is_per_instance(self):
        a, b = RecordingHardware(), RecordingHardware()
        a.emergency_stop()
        b.send(StandCommand.ROTATE_CW)
        assert b.sent == [StandCommand.ROTATE_CW]
