"""Streaming raw-PCM playback helpers for the named Shokz USB headset."""

from __future__ import annotations

import math
import shutil
import struct
import subprocess
from typing import BinaryIO

from .devices import find_alsa_playback, find_pulse_playback


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
) -> subprocess.Popen:
    return subprocess.Popen(
        raw_playback_command(output_device_name, sample_rate, channels),
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def finish_raw_player(process: subprocess.Popen, timeout_s: float = 15.0) -> bool:
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
) -> bool:
    process = open_raw_player(output_device_name, sample_rate)
    try:
        if process.stdin is None:
            return False
        process.stdin.write(pcm_s16le)
        return finish_raw_player(process)
    except (BrokenPipeError, OSError):
        process.kill()
        process.wait(timeout=2)
        return False
