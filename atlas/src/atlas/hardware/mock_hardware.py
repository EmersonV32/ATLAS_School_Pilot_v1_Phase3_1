"""Mock hardware adapter — logs all commands, no Bluetooth required."""

from __future__ import annotations

import logging

from .base import BaseHardware, StandCommand

logger = logging.getLogger(__name__)


class MockHardware(BaseHardware):
    """No-op adapter. Prints commands to console. Safe on Windows/Mac/Linux."""

    def _send_command(self, command: StandCommand, stand_id: int = 1) -> None:
        logger.info("[HW] Stand %d → %s", stand_id, command.value)
        print(f"[HW] Stand {stand_id} -> {command.value}")

    def set_status_led(self, colour: str) -> None:
        logger.info("[HW] LED → %s", colour)
        print(f"[HW] LED -> {colour}")

    def focus_artwork(self, artwork_id: str) -> None:
        logger.info("[HW] Focus artwork -> %s", artwork_id)
        print(f"[HW] Focus artwork -> {artwork_id}")

    def reset_exhibit(self) -> None:
        logger.info("[HW] All artworks up")
        print("[HW] All artworks up")
