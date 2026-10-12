"""Bounded camera-pan motion, independent of voice and exhibit rotation.

SG90 is open-loop: angles describe commands, not measured camera positions.
Only the worker generates movement. Dashboard jogs use a server-side lease.
"""

from __future__ import annotations

import math
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from uuid import uuid4

from atlas.config.settings import CameraPanSettings
from atlas.hardware.camera_pan_driver import PanDriver


class CameraPanController:
    TICK_S = 0.05
    JOG_LEASE_S = 0.6

    def __init__(
        self,
        settings: CameraPanSettings,
        driver: PanDriver,
        *,
        simulated: bool,
        emergency_guard: Callable[[], bool] = lambda: False,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self.driver = driver
        self.simulated = simulated
        self._emergency_guard = emergency_guard
        self._clock = clock
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._mode = "disabled" if not settings.enabled else "not_started"
        self._angle = settings.center_angle
        self._target = settings.max_angle
        self._jog = 0
        self._lease_until = 0.0
        self._opened = False
        self._estop = False
        self._fault = ""
        self._sequences: OrderedDict[str, int] = OrderedDict()
        self._control_epoch = str(uuid4())

    def start(self, *, background: bool = True) -> None:
        with self._lock:
            if self._mode != "not_started":
                return
            if not self.simulated and not self.settings.calibration_confirmed:
                self._mode = "uncalibrated"
                return
            try:
                if self._estop or self._emergency_guard():
                    self._mode = "emergency_stopped"
                    self._estop = True
                    return
                self.driver.open()
                self._opened = True
                self._write_angle()
                self._mode = "sweep"
                if background:
                    self._thread = threading.Thread(
                        target=self._run,
                        name="atlas-camera-pan",
                        daemon=True,
                    )
                    self._thread.start()
            except Exception:
                self._fail()

    def _write_angle(self) -> None:
        cfg = self.settings
        fraction = (self._angle - cfg.min_angle) / (cfg.max_angle - cfg.min_angle)
        self.driver.write_pulse(
            cfg.min_pulse_us + fraction * (cfg.max_pulse_us - cfg.min_pulse_us)
        )

    def _fail(self) -> None:
        self._mode = "fault"
        self._fault = "Servo unavailable. Check wiring/configuration; restart ATLAS."
        self._stop.set()
        try:
            self.driver.disable()
        except Exception:
            self._fault += " PWM disable unconfirmed; cut servo power."
        try:
            self.driver.close()
        except Exception:
            pass
        self._opened = False

    def _run(self) -> None:
        previous = self._clock()
        while not self._stop.wait(self.TICK_S):
            now = self._clock()
            self.tick(now - previous, now=now)
            previous = now

    def tick(self, elapsed_s: float, *, now: float | None = None) -> None:
        """Deterministic motion step; cap elapsed time to avoid catch-up jumps."""
        with self._lock:
            if not self._opened or self._stop.is_set() or self._estop:
                return
            try:
                if self._emergency_guard():
                    self.emergency_stop()
                    return
                now = self._clock() if now is None else now
                dt = min(0.1, max(0.0, elapsed_s))
                if self._mode == "jog" and now >= self._lease_until:
                    self._mode = "hold"
                if self._mode not in {"sweep", "position", "jog"}:
                    return
                cfg = self.settings
                if self._mode == "jog":
                    target = cfg.max_angle if self._jog > 0 else cfg.min_angle
                else:
                    target = self._target
                speed = (
                    cfg.sweep_speed_deg_s
                    if self._mode == "sweep"
                    else cfg.manual_speed_deg_s
                )
                delta = max(-speed * dt, min(speed * dt, target - self._angle))
                if delta:
                    self._angle = max(
                        cfg.min_angle, min(cfg.max_angle, self._angle + delta)
                    )
                    self._write_angle()
                if abs(self._angle - target) < 0.00001:
                    if self._mode == "sweep":
                        self._target = (
                            cfg.min_angle if target == cfg.max_angle else cfg.max_angle
                        )
                    elif self._mode == "position":
                        self._mode = "hold"
            except Exception:
                self._fail()

    def command(
        self,
        action: str,
        *,
        client_id: str,
        sequence: int,
        control_epoch: str,
        angle: float | None = None,
        direction: int | None = None,
    ) -> dict:
        with self._lock:
            if self._emergency_guard():
                self.emergency_stop()
            if self._estop:
                raise RuntimeError("Clear emergency stop, then explicitly resume pan.")
            if control_epoch != self._control_epoch:
                raise RuntimeError("Pan state changed. Refresh before controlling it.")
            if self._mode in {
                "disabled",
                "not_started",
                "uncalibrated",
                "fault",
                "stopped",
            }:
                raise RuntimeError("Camera pan is not ready; check its status.")
            # Reject delayed/out-of-order packets, including renewals after release.
            if sequence <= self._sequences.get(client_id, -1):
                raise ValueError("Stale camera pan command")
            if action not in {"sweep", "hold", "center", "position", "jog"}:
                raise ValueError("Unknown camera pan action")
            if action == "position" and (
                angle is None
                or not math.isfinite(angle)
                or not self.settings.min_angle <= angle <= self.settings.max_angle
            ):
                raise ValueError("Angle outside calibrated travel limits")
            if action == "jog" and direction not in {-1, 1}:
                raise ValueError("Jog direction must be -1 or 1")
            self._sequences[client_id] = sequence
            self._sequences.move_to_end(client_id)
            if len(self._sequences) > 64:
                self._sequences.popitem(last=False)
            if action == "sweep":
                self._target = self.settings.max_angle
                self._mode = "sweep"
            elif action in {"center", "position"}:
                self._target = (
                    self.settings.center_angle if action == "center" else angle
                )
                self._mode = "position"
            elif action == "jog":
                self._jog = direction
                self._lease_until = self._clock() + self.JOG_LEASE_S
                self._mode = "jog"
            else:
                self._mode = "hold"
            # Clear-stop releases PWM; explicit movement re-arms at the last command.
            if self._mode != "hold":
                try:
                    self._write_angle()
                except Exception:
                    self._fail()
                    raise RuntimeError(
                        "Servo unavailable; cut power if needed."
                    ) from None
            return self.status()

    def emergency_stop(self) -> None:
        with self._lock:
            self._estop = True
            self._control_epoch = str(uuid4())
            self._jog = 0
            if self._mode not in {"disabled", "fault", "stopped", "uncalibrated"}:
                self._mode = "emergency_stopped"
            if self._opened:
                try:
                    self.driver.disable()
                except Exception:
                    self._fail()

    def clear_emergency_stop(self) -> None:
        with self._lock:
            self._estop = False
            self._control_epoch = str(uuid4())
            if self._mode == "emergency_stopped":
                # Never automatically resume after a safety stop.
                self._mode = "hold" if self._opened else "not_started"

    def status(self) -> dict:
        with self._lock:
            return {
                "enabled": self.settings.enabled,
                "simulated": self.simulated,
                "ready": self._opened and not self._estop and self._mode != "fault",
                "mode": self._mode,
                "commanded_angle": round(self._angle, 1),
                "min_angle": self.settings.min_angle,
                "max_angle": self.settings.max_angle,
                "emergency_stopped": self._estop,
                "detail": self._fault
                or (
                    "Calibration required; restart after verifying the mount."
                    if self._mode == "uncalibrated"
                    else "Disabled in configuration."
                    if self._mode == "disabled"
                    else "Simulation only; no motor connected."
                    if self.simulated
                    else "Open-loop commanded angle, not a measured position."
                ),
                "control_epoch": self._control_epoch,
            }

    def close(self) -> None:
        self._stop.set()
        with self._lock:
            if self._opened:
                try:
                    self.driver.disable()
                    self.driver.close()
                except Exception:
                    self._fail()
            self._opened = False
            if self._mode != "fault":
                self._mode = "stopped" if self.settings.enabled else "disabled"
        if self._thread is not None:
            self._thread.join(timeout=2.0)
