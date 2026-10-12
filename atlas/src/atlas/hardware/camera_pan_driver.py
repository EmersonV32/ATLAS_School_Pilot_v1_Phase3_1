"""Optional hardware PWM; no GPIO bit-banging, media, or exhibit motor changes.

The PCA9685 must be dedicated to this camera. Its frequency is board-wide.
All writes use the configured address; shutdown disables only our channel.
Direct Jetson PWM uses the Linux kernel, no GPIO library or extra board.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Protocol

from atlas.config.settings import CameraPanSettings


class PanDriver(Protocol):
    def open(self) -> None: ...
    def write_pulse(self, pulse_us: float) -> None: ...
    def disable(self) -> None: ...
    def close(self) -> None: ...


class MockPanDriver:
    """In-memory simulation. Never imports or opens a hardware library."""

    def __init__(self) -> None:
        self.pulse_us: float | None = None

    def open(self) -> None:
        pass

    def write_pulse(self, pulse_us: float) -> None:
        self.pulse_us = pulse_us

    def disable(self) -> None:
        self.pulse_us = None

    def close(self) -> None:
        self.disable()


JETSON_HEADER_PWM = {15: "3280000.pwm", 32: "32e0000.pwm"}


class _LinuxPWMChannel:
    """Own one newly exported PWM channel; refuse any already exported channel.

    Controller identity, not unstable pwmchip numbering, determines routing.
    No fan controller, device-tree changes, root commands, or shared GPIO cleanup.
    sysfs_root/ownership_factory are test-only injection points, not configuration.
    """

    PERIOD_NS = 20_000_000  # fixed 50 Hz SG90 control waveform

    def __init__(self, identity: str, *, sysfs_root=None, ownership_factory=None):
        if identity not in JETSON_HEADER_PWM.values():
            raise ValueError("Unsupported header PWM controller")
        self.identity = identity
        self._root = Path(sysfs_root or "/sys/class/pwm")
        self._ownership_factory = ownership_factory
        self._ownership = None
        self._chip = None
        self._channel = None
        self._exported = False

    def _claim(self):
        if self._ownership_factory is not None:
            return self._ownership_factory(self.identity)
        import fcntl
        import os
        import tempfile

        path = Path(tempfile.gettempdir()) / (
            f"atlas-camera-pan-pwm-{os.getuid()}-{self.identity}.lock"
        )
        ownership = path.open("a")
        try:
            fcntl.flock(ownership, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            ownership.close()
            raise RuntimeError(
                "Header PWM already owned by another ATLAS process"
            ) from None
        return ownership

    def _write(self, name: str, value: int | str) -> None:
        if self._channel is None:
            raise RuntimeError("Header PWM not open")
        (self._channel / name).write_text(str(value), encoding="ascii")

    def open(self) -> None:
        if self._exported:
            return
        chips = [
            chip
            for chip in self._root.glob("pwmchip*")
            if (chip / "device").resolve().name == self.identity
        ]
        if len(chips) != 1:
            raise RuntimeError("Expected header PWM controller is unavailable")
        chip = chips[0]
        if int((chip / "npwm").read_text(encoding="ascii")) != 1:
            raise RuntimeError("Unexpected header PWM channel count")
        self._ownership = self._claim()
        self._chip = chip
        self._channel = chip / "pwm0"
        try:
            # Never adopt a PWM owned by a fan, another program, or stale run.
            if self._channel.exists():
                raise RuntimeError("Header PWM is already exported; inspect its owner")
            (chip / "export").write_text("0", encoding="ascii")
            self._exported = True
            deadline = time.monotonic() + 1.0
            while not (self._channel / "enable").exists():
                if time.monotonic() >= deadline:
                    raise RuntimeError("Header PWM export did not become ready")
                time.sleep(0.01)
            self._write("enable", 0)
            self._write("duty_cycle", 0)
            self._write("polarity", "normal")
            self._write("period", self.PERIOD_NS)
        except Exception:
            self.close()
            raise

    def write_pulse(self, pulse_ns: int) -> None:
        if not self._exported or not 500_000 <= pulse_ns <= 2_500_000:
            raise ValueError("Invalid or unavailable header PWM pulse")
        self._write("duty_cycle", pulse_ns)
        self._write("enable", 1)

    def disable(self) -> None:
        if self._exported:
            # Duty zero before disable; disabling alone need not drive low.
            try:
                self._write("duty_cycle", 0)
            finally:
                self._write("enable", 0)

    def close(self) -> None:
        try:
            if self._exported:
                try:
                    self.disable()
                finally:
                    (self._chip / "unexport").write_text("0", encoding="ascii")
        finally:
            self._exported = False
            self._chip = self._channel = None
            if self._ownership is not None:
                self._ownership.close()
                self._ownership = None


class JetsonPWMPanDriver:
    """Direct reComputer Super J401: kernel PWM, never software-timed pulses."""

    def __init__(self, settings: CameraPanSettings, channel_factory=None):
        self.settings = settings
        self._channel_factory = channel_factory or _LinuxPWMChannel
        self._channel = None
        self._last_ns = None

    def open(self) -> None:
        if self._channel is not None:
            return
        cfg = self.settings
        if not cfg.pinmux_confirmed or not cfg.power_confirmed:
            raise RuntimeError("Verify header PWM routing and servo power first")
        channel = self._channel_factory(JETSON_HEADER_PWM[cfg.jetson_board_pin])
        # Retain a partially opened channel so failure/shutdown can release it.
        self._channel = channel
        channel.open()

    def write_pulse(self, pulse_us: float) -> None:
        if self._channel is None:
            raise RuntimeError("Header PWM is not open")
        if not math.isfinite(pulse_us) or not (
            self.settings.min_pulse_us <= pulse_us <= self.settings.max_pulse_us
        ):
            raise ValueError("Camera pan pulse outside calibrated limits")
        pulse_ns = round(pulse_us * 1000)
        if pulse_ns != self._last_ns:
            self._channel.write_pulse(pulse_ns)
            self._last_ns = pulse_ns

    def disable(self) -> None:
        self._last_ns = None
        if self._channel is not None:
            self._channel.disable()

    def close(self) -> None:
        try:
            if self._channel is not None:
                self._channel.close()
        finally:
            self._channel = None
            self._last_ns = None


class PCA9685PanDriver:
    def __init__(self, settings: CameraPanSettings, bus_factory=None) -> None:
        self.settings = settings
        self._bus_factory = bus_factory
        self._bus = None
        self._ownership = None
        self._last_ticks = None
        self._prescale = round(settings.oscillator_hz / (4096 * 50)) - 1

    def open(self) -> None:
        if self._bus is not None:
            return
        if self.settings.i2c_bus is None:
            raise RuntimeError("camera pan I2C bus is not configured")
        # Test injection bypasses Linux-only device ownership/imports.
        if self._bus_factory is None:
            import fcntl
            import os
            import tempfile
            from pathlib import Path

            from smbus2 import SMBus

            path = Path(tempfile.gettempdir()) / (
                f"atlas-camera-pan-{os.getuid()}-{self.settings.i2c_bus}-"
                f"{self.settings.i2c_address}.lock"
            )
            self._ownership = path.open("a")
            try:
                fcntl.flock(self._ownership, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except Exception:
                self._ownership.close()
                self._ownership = None
                raise
            bus_factory = SMBus
        else:
            bus_factory = self._bus_factory
        try:
            self._bus = bus_factory(self.settings.i2c_bus)
            addr = self.settings.i2c_address
            mode = self._bus.read_byte_data(addr, 0x00)
            if mode & 0x40:
                raise RuntimeError("external-clock PCA9685 is not supported")
            # Refuse an active shared board before changing its common frequency.
            for channel in range(16):
                if channel == self.settings.channel:
                    continue
                values = [
                    self._bus.read_byte_data(addr, 6 + 4 * channel + i)
                    for i in range(4)
                ]
                if not values[3] & 0x10 and (
                    values[1] & 0x10 or values[:2] != values[2:]
                ):
                    raise RuntimeError("PCA9685 has another active channel")
            if any(self._bus.read_byte_data(addr, reg) & 0x10 for reg in (0xFB, 0xFD)):
                raise RuntimeError("PCA9685 global override is set; power-cycle it")
            self.disable()
            # Internal oscillator; no broadcast reset or ALL_LED writes.
            awake = (mode & 0x0F) | 0x20
            self._bus.write_byte_data(addr, 0x00, awake | 0x10)
            self._bus.write_byte_data(addr, 0xFE, self._prescale)
            self._bus.write_byte_data(addr, 0x01, 0x04)  # totem pole, STOP update
            self._bus.write_byte_data(addr, 0x00, awake)
            time.sleep(0.001)  # datasheet oscillator stabilization >= 500 us
            self._bus.write_byte_data(addr, 0x00, awake | 0x80)
        except Exception:
            self.close()
            raise

    def write_pulse(self, pulse_us: float) -> None:
        if self._bus is None:
            raise RuntimeError("camera pan PWM is not open")
        if not math.isfinite(pulse_us) or not (
            self.settings.min_pulse_us <= pulse_us <= self.settings.max_pulse_us
        ):
            raise ValueError("camera pan pulse outside calibrated limits")
        ticks = round(
            pulse_us * self.settings.oscillator_hz / (1_000_000 * (self._prescale + 1))
        )
        if ticks == self._last_ticks:
            return
        self._bus.write_i2c_block_data(
            self.settings.i2c_address,
            6 + 4 * self.settings.channel,
            [0, 0, ticks & 0xFF, (ticks >> 8) & 0x0F],
        )
        self._last_ticks = ticks

    def disable(self) -> None:
        if self._bus is not None:
            # A single-register write works even before MODE1 auto-increment
            # is enabled at startup. FULL_OFF overrides any old channel PWM.
            self._bus.write_byte_data(
                self.settings.i2c_address,
                9 + 4 * self.settings.channel,
                0x10,
            )
        self._last_ticks = None

    def close(self) -> None:
        try:
            if self._bus is not None:
                self._bus.close()
        finally:
            self._bus = None
            self._last_ticks = None
            if self._ownership is not None:
                self._ownership.close()
                self._ownership = None
