"""EV3 adapter for the proven ATLAS Pybricks text-mailbox protocol."""

from __future__ import annotations

import logging
import socket
import struct
import threading
import time

from .base import BaseHardware, StandCommand

logger = logging.getLogger(__name__)

_SYSTEM_COMMAND_NO_REPLY = 0x81
_WRITE_MAILBOX = 0x9E
_RFCOMM_CHANNEL = 1

_ARTWORK_TO_SLOT = {
    "starry_night": "slot_1",  # EV3 port A
    "mona_lisa": "slot_2",  # EV3 port B
    "tutankhamun_mask": "slot_3",  # EV3 port C
    "pharaoh_mask": "slot_3",
}


class _MailboxClient:
    """Minimal Pybricks v2-compatible text mailbox client.

    Framing follows the MIT-licensed Pybricks v2.0 messaging implementation:
    https://github.com/pybricks/pybricks-micropython
    """

    def __init__(self, address: str, timeout_s: float) -> None:
        self.socket = socket.socket(
            socket.AF_BLUETOOTH,
            socket.SOCK_STREAM,
            socket.BTPROTO_RFCOMM,
        )
        self.socket.settimeout(timeout_s)
        self.socket.connect((address, _RFCOMM_CHANNEL))

    def _recv_exact(self, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            chunk = self.socket.recv(size - len(data))
            if not chunk:
                raise ConnectionError("EV3 closed the Bluetooth connection")
            data.extend(chunk)
        return bytes(data)

    def _receive_text(self, mailbox_name: str) -> str:
        message_size = struct.unpack("<H", self._recv_exact(2))[0]
        message = self._recv_exact(message_size)
        _count, command_type, command, name_size = struct.unpack("<HBBB", message[:5])
        if command_type != _SYSTEM_COMMAND_NO_REPLY or command != _WRITE_MAILBOX:
            raise ValueError("unexpected EV3 mailbox response")
        name = message[5 : 5 + name_size].decode().rstrip("\0")
        if name != mailbox_name:
            raise ValueError(f"unexpected EV3 mailbox name: {name!r}")
        data_start = 5 + name_size
        data_size = struct.unpack("<H", message[data_start : data_start + 2])[0]
        payload = message[data_start + 2 : data_start + 2 + data_size]
        return payload.decode().rstrip("\0")

    def send_text(self, mailbox_name: str, value: str) -> None:
        name = (mailbox_name + "\0").encode()
        payload = (value + "\0").encode()
        send_len = 7 + len(name) + len(payload)
        packet = struct.pack(
            f"<HHBBB{len(name)}sH{len(payload)}s",
            send_len,
            1,
            _SYSTEM_COMMAND_NO_REPLY,
            _WRITE_MAILBOX,
            len(name),
            name,
            len(payload),
            payload,
        )
        self.socket.sendall(packet)

    def exchange(self, mailbox_name: str, value: str) -> str:
        self.send_text(mailbox_name, value)
        return self._receive_text(mailbox_name)

    def close(self) -> None:
        self.socket.close()


class EV3Hardware(BaseHardware):
    """Send text commands understood by ``ev3/ev3_motors.py``.

    Pybricks mailbox framing is required by the working EV3 program. Raw
    RFCOMM packets are not protocol-compatible with that server.
    """

    def __init__(
        self,
        bt_address: str,
        mailbox_name: str = "atlas",
        connect_timeout_s: float = 12.0,
        status_led_enabled: bool = False,
    ) -> None:
        self._address = bt_address
        self._mailbox_name = mailbox_name
        self._connect_timeout_s = connect_timeout_s
        self._status_led_enabled = status_led_enabled
        self._client: _MailboxClient | None = None
        self._lock = threading.RLock()

    @property
    def connected(self) -> bool:
        return self._client is not None

    def _connect(self) -> None:
        if self.connected:
            return
        started = time.monotonic()
        client = _MailboxClient(self._address, self._connect_timeout_s)
        if time.monotonic() - started > self._connect_timeout_s:
            logger.warning("EV3 connection exceeded configured timeout")
        # The first mailbox message can be discarded by this EV3 stack. Send
        # a warm-up ping and accept either a reply or one short timeout.
        client.send_text(self._mailbox_name, "ping")
        client.socket.settimeout(1.0)
        try:
            client._receive_text(self._mailbox_name)
        except TimeoutError:
            pass
        finally:
            client.socket.settimeout(self._connect_timeout_s)
        self._client = client
        logger.info("EV3 mailbox connected at %s", self._address)

    def warm_up(self) -> None:
        with self._lock:
            self._connect()
            if not self._send_text("ping", reconnect=False, quiet=True):
                raise RuntimeError("EV3 did not answer ping")

    def _disconnect(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except OSError:
                pass
        self._client = None

    def _send_text(
        self, command: str, reconnect: bool = True, quiet: bool = False
    ) -> bool:
        with self._lock:
            try:
                self._connect()
                reply = self._client.exchange(self._mailbox_name, command)
                if reply in ("ok", "pong"):
                    return True
                if not quiet:
                    logger.warning("EV3 rejected %r: %r", command, reply)
            except Exception as exc:
                if not quiet:
                    logger.warning("EV3 command %r failed: %s", command, exc)
                self._disconnect()
                if reconnect:
                    try:
                        self._connect()
                        reply = self._client.exchange(self._mailbox_name, command)
                        return reply in ("ok", "pong")
                    except Exception as retry_exc:
                        logger.warning("EV3 retry failed: %s", retry_exc)
                        self._disconnect()
            return False

    def _send_command(self, command: StandCommand, stand_id: int = 1) -> None:
        if command == StandCommand.CENTER:
            self.reset_exhibit()
        elif command == StandCommand.RELEASE:
            self._send_text("lower_all")
        else:
            logger.info("EV3 generic command ignored: %s", command.value)

    def focus_artwork(self, artwork_id: str) -> None:
        if self.emergency_stopped:
            logger.warning("EV3 focus blocked by emergency stop")
            return
        slot = _ARTWORK_TO_SLOT.get(artwork_id)
        if slot is None:
            logger.warning("No EV3 slot configured for artwork %r", artwork_id)
            return
        self._send_text(f"raise:{slot}")

    def reset_exhibit(self) -> None:
        if not self.emergency_stopped:
            self._send_text("raise_all")

    def set_status_led(self, colour: str) -> None:
        if self._status_led_enabled:
            self._send_text(f"status:{colour}", quiet=True)

    def close(self) -> None:
        with self._lock:
            self._disconnect()
