"""Abstract hardware interface and StandCommand enum."""
from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum


class StandCommand(Enum):
    ROTATE_CW  = "rotate_cw"
    ROTATE_CCW = "rotate_ccw"
    CENTER     = "center"
    LOCK       = "lock"
    RELEASE    = "release"


class BaseHardware(ABC):
    @abstractmethod
    def send(self, command: StandCommand, stand_id: int = 1) -> None:
        """Send a motor command to EV3 painting stand stand_id."""
        ...

    @abstractmethod
    def set_status_led(self, colour: str) -> None:
        """
        Set the status indicator.
        colour: "green" | "amber" | "red" | "off"
        On Jetson: uses EV3 LED over Bluetooth (avoids JetPack 6.x GPIO pinmux bug).
        """
        ...
