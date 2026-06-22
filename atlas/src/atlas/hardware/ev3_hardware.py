"""
EV3 hardware adapter — Bluetooth RFCOMM socket.

Protocol note: the EV3 side must be programmed to receive and act on this
message format. Each message is a 5-byte packet:
  [0] stand_id  (uint8)
  [1] cmd_byte  (first byte of StandCommand.value ASCII)
  [2-3] duration_ms (uint16 big-endian)
  [4] direction (int8: 1=CW, -1=CCW, 0=stop)

LED messages are prefixed with 0xFF:
  [0] 0xFF
  [1] colour_code (0=off, 1=green, 2=amber, 3=red)

Pair the EV3 to the Jetson first:
  bluetoothctl -> pair <EV3_MAC> -> trust <EV3_MAC>
"""
from __future__ import annotations
import logging
import socket
import struct
from .base import BaseHardware, StandCommand

logger = logging.getLogger(__name__)

_CMD_PARAMS: dict[StandCommand, tuple[int, int]] = {
    StandCommand.ROTATE_CW:  (800, 1),
    StandCommand.ROTATE_CCW: (800, -1),
    StandCommand.CENTER:     (400, 0),
    StandCommand.LOCK:       (0, 0),
    StandCommand.RELEASE:    (0, 0),
}
_LED_CODES = {"off": 0, "green": 1, "amber": 2, "red": 3}


class EV3Hardware(BaseHardware):
    """
    bt_address: EV3 Bluetooth MAC address (e.g. "00:16:53:XX:XX:XX")
    port: RFCOMM channel (default 1, check your EV3 program)
    """

    def __init__(self, bt_address: str, port: int = 1) -> None:
        self._addr = bt_address
        self._port = port
        self._sock: socket.socket | None = None

    def _connect(self) -> None:
        if self._sock is not None:
            return
        try:
            self._sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            self._sock.settimeout(5.0)
            self._sock.connect((self._addr, self._port))
            logger.info("EV3 connected: %s port %d", self._addr, self._port)
        except OSError as exc:
            logger.error("EV3 connect failed: %s", exc)
            self._sock = None
            raise

    def _send_raw(self, payload: bytes) -> None:
        try:
            self._connect()
            self._sock.sendall(payload)
        except Exception as exc:
            logger.warning("EV3 send failed: %s — closing socket", exc)
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def send(self, command: StandCommand, stand_id: int = 1) -> None:
        duration_ms, direction = _CMD_PARAMS.get(command, (0, 0))
        cmd_byte = command.value.encode()[0]
        payload = struct.pack(">BBHb", stand_id, cmd_byte, duration_ms, direction)
        self._send_raw(payload)

    def set_status_led(self, colour: str) -> None:
        code = _LED_CODES.get(colour, 0)
        self._send_raw(struct.pack("BB", 0xFF, code))
