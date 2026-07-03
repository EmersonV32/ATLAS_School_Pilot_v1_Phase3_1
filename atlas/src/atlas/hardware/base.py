"""Abstract hardware interface and StandCommand enum.

Safety model:
  - `send()` is the ONLY path for motor commands, and it refuses while the
    emergency stop is active. Adapters implement `_send_command()` and must
    never expose another movement path.
  - Hardware commands come only from the session runner / dashboard —
    never from LLM output.
"""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class StandCommand(Enum):
    ROTATE_CW  = "rotate_cw"
    ROTATE_CCW = "rotate_ccw"
    CENTER     = "center"
    LOCK       = "lock"
    RELEASE    = "release"


class BaseHardware(ABC):
    # Class-level default so adapters need not call super().__init__().
    _emergency_stopped: bool = False

    def send(self, command: StandCommand, stand_id: int = 1) -> None:
        """Send a motor command to EV3 painting stand stand_id.

        Blocked while the emergency stop is active.
        """
        if self._emergency_stopped:
            logger.warning(
                "EMERGENCY STOP active — motor command %s blocked.", command.value
            )
            return
        self._send_command(command, stand_id)

    @abstractmethod
    def _send_command(self, command: StandCommand, stand_id: int = 1) -> None:
        """Adapter-specific motor implementation. Do not call directly."""
        ...

    @abstractmethod
    def set_status_led(self, colour: str) -> None:
        """
        Set the status indicator.
        colour: "green" | "amber" | "red" | "off"
        On Jetson: uses EV3 LED over Bluetooth. The KY-016 RGB LED GPIO is
        broken on JetPack 6.x (pins 29/31/33) — the EV3 LED replaces it and
        is not critical path.
        """
        ...

    # -- emergency stop ----------------------------------------------------
    def emergency_stop(self) -> None:
        """Latch the emergency stop: all movement is refused until cleared."""
        self._emergency_stopped = True
        logger.warning("EMERGENCY STOP engaged.")
        try:
            self.set_status_led("red")
        except Exception:  # LED failure must not mask the stop
            pass

    def clear_emergency_stop(self) -> None:
        self._emergency_stopped = False
        logger.info("Emergency stop cleared.")
        try:
            self.set_status_led("off")
        except Exception:
            pass

    @property
    def emergency_stopped(self) -> bool:
        return self._emergency_stopped
