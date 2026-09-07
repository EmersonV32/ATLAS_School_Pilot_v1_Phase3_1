"""Streaming raw-PCM playback helpers for the named Shokz USB headset."""

from __future__ import annotations

import math
import shutil
import struct
import subprocess
import time
from array import array
from typing import Any, BinaryIO

from .devices import find_alsa_playback, find_pulse_playback

_OUTPUT_DEVICE_SEPARATOR = "|||"


def join_output_device_names(*names: str) -> str:
    """Encode one or more playback targets in the existing TTS string API."""
    return _OUTPUT_DEVICE_SEPARATOR.join(name.strip() for name in names if name.strip())


def split_output_device_names(value: str) -> tuple[str, ...]:
    """Decode playback targets while preserving compatibility with one device."""
    return tuple(
        dict.fromkeys(
            name.strip()
            for name in str(value).split(_OUTPUT_DEVICE_SEPARATOR)
            if name.strip()
        )
    )


class _FanoutWriter:
    def __init__(self, streams: list[BinaryIO]) -> None:
        self._streams = streams

    @property
    def closed(self) -> bool:
        return all(stream.closed for stream in self._streams)

    def write(self, data: bytes) -> int:
        error: OSError | None = None
        for stream in self._streams:
            try:
                stream.write(data)
            except OSError as exc:
                error = exc
        if error is not None:
            raise error
        return len(data)

    def close(self) -> None:
        for stream in self._streams:
            if not stream.closed:
                stream.close()


class _PlaybackGroup:
    """Small Popen-compatible facade that writes PCM to several players."""

    def __init__(self, processes: list[subprocess.Popen]) -> None:
        self.processes = processes
        self.stdin = _FanoutWriter(
            [process.stdin for process in processes if process.stdin is not None]
        )

    @property
    def returncode(self) -> int | None:
        codes = [process.returncode for process in self.processes]
        if any(code is None for code in codes):
            return None
        return 0 if all(code == 0 for code in codes) else 1

    def poll(self) -> int | None:
        codes = [process.poll() for process in self.processes]
        return None if any(code is None for code in codes) else self.returncode

    def wait(self, timeout: float | None = None) -> int:
        deadline = None if timeout is None else time.monotonic() + timeout
        for process in self.processes:
            remaining = (
                None
                if deadline is None
                else max(0.0, deadline - time.monotonic())
            )
            process.wait(timeout=remaining)
        return int(self.returncode or 0)

    def kill(self) -> None:
        for process in self.processes:
            if process.poll() is None:
                process.kill()


def normalize_volume(volume_percent: int) -> int:
    return min(100, max(0, int(volume_percent)))


def scale_pcm_s16le(pcm_s16le: bytes, volume_percent: int) -> bytes:
    """Apply deterministic software gain to little-endian signed 16-bit PCM."""
    volume = normalize_volume(volume_percent)
    if volume >= 100 or not pcm_s16le:
        return pcm_s16le
    samples = array("h")
    samples.frombytes(pcm_s16le)
    if struct.pack("=h", 1) != struct.pack("<h", 1):
        samples.byteswap()
    gain = volume / 100.0
    for index, sample in enumerate(samples):
        samples[index] = int(sample * gain)
    if struct.pack("=h", 1) != struct.pack("<h", 1):
        samples.byteswap()
    return samples.tobytes()


def raw_playback_command(
    output_device_name: str,
    sample_rate: int,
    channels: int = 1,
) -> list[str]:
    pulse_device = find_pulse_playback(output_device_name)
    if pulse_device and shutil.which("paplay"):
        return [
            "paplay",
            f"--device={pulse_device}",
            "--raw",
            "--format=s16le",
            f"--rate={sample_rate}",
            f"--channels={channels}",
        ]

    command = [
        "aplay",
        "-q",
        "-t",
        "raw",
        "-f",
        "S16_LE",
        "-r",
        str(sample_rate),
        "-c",
        str(channels),
    ]
    alsa_device = find_alsa_playback(output_device_name)
    if alsa_device:
        command[1:1] = ["-D", alsa_device]
    return command


def open_raw_player(
    output_device_name: str,
    sample_rate: int,
    channels: int = 1,
) -> Any:
    names = split_output_device_names(output_device_name)
    if not names:
        names = (output_device_name,)
    processes: list[subprocess.Popen] = []
    try:
        for name in names:
            processes.append(
                subprocess.Popen(
                    raw_playback_command(name, sample_rate, channels),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            )
    except Exception:
        for process in processes:
            process.kill()
        raise
    return processes[0] if len(processes) == 1 else _PlaybackGroup(processes)


def finish_raw_player(process: Any, timeout_s: float = 15.0) -> bool:
    stdin: BinaryIO | None = process.stdin
    if stdin is not None and not stdin.closed:
        stdin.close()
    try:
        process.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
    return process.returncode == 0


def listening_cue_pcm(sample_rate: int = 16000) -> bytes:
    """Generate the same short two-note cue without touching the network."""
    frames = bytearray()
    amplitude = 7000
    for frequency, duration in ((660.0, 0.09), (880.0, 0.12)):
        count = int(sample_rate * duration)
        for index in range(count):
            edge = min(index, count - index - 1, 80) / 80.0
            sample = int(
                amplitude
                * max(0.0, edge)
                * math.sin(2.0 * math.pi * frequency * index / sample_rate)
            )
            frames.extend(struct.pack("<h", sample))
    return bytes(frames)


def play_pcm(
    pcm_s16le: bytes,
    output_device_name: str,
    sample_rate: int,
    volume_percent: int = 100,
) -> bool:
    process = open_raw_player(output_device_name, sample_rate)
    try:
        if process.stdin is None:
            return False
        process.stdin.write(scale_pcm_s16le(pcm_s16le, volume_percent))
        return finish_raw_player(process)
    except (BrokenPipeError, OSError):
        process.kill()
        process.wait(timeout=2)
        return False
