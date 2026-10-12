"""Optional hardware PWM; no GPIO bit-banging, media, or exhibit motor changes.

The PCA9685 must be dedicated to this camera. Its frequency is board-wide.
All writes use the configured address; shutdown disables only our channel.
"""

from __future__ import annotations

import time
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
        if not self.settings.min_pulse_us <= pulse_us <= self.settings.max_pulse_us:
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
