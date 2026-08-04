#!/usr/bin/env python3
"""Route the Shokz microphone to its headset output for a timed test."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

import numpy as np
import sounddevice as sd


def score_device(name: str, requested: str) -> int:
    candidate = name.lower()
    tokens = ("shokz", "loop", "opencomm")
    score = sum(3 for token in tokens if token in candidate)
    if requested.lower() in candidate:
        score += 10
    return score


def pulse_default(direction: str) -> str:
    label = "Default Source" if direction == "input" else "Default Sink"
    try:
        result = subprocess.run(
            ["pactl", "info"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    for line in result.stdout.splitlines():
        name, separator, value = line.partition(":")
        if separator and name.strip() == label:
            return value.strip()
    return ""


def find_device(requested: str, channel_key: str) -> tuple[int, dict[str, object]]:
    devices = list(sd.query_devices())
    direction = "input" if channel_key == "max_input_channels" else "output"
    if score_device(pulse_default(direction), requested):
        for preferred_name in ("pulse", "default"):
            for index, raw_info in enumerate(devices):
                info = dict(raw_info)
                if (
                    int(info.get(channel_key, 0)) >= 1
                    and str(info.get("name", "")).lower() == preferred_name
                ):
                    return index, info

    candidates: list[tuple[int, int, dict[str, object]]] = []
    for index, raw_info in enumerate(devices):
        info = dict(raw_info)
        if int(info.get(channel_key, 0)) < 1:
            continue
        score = score_device(str(info.get("name", "")), requested)
        if score:
            candidates.append((score, index, info))
    if not candidates:
        raise RuntimeError(f"No Shokz {direction} device was found")
    _, index, info = max(candidates, key=lambda item: item[0])
    return index, info


def choose_sample_rate(input_index: int, output_index: int) -> int:
    for sample_rate in (48000, 44100):
        try:
            sd.check_input_settings(
                device=input_index, channels=1, dtype="float32", samplerate=sample_rate
            )
            sd.check_output_settings(
                device=output_index,
                channels=2,
                dtype="float32",
                samplerate=sample_rate,
            )
        except sd.PortAudioError:
            continue
        return sample_rate
    raise RuntimeError("Shokz input and output have no compatible sample rate")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--gain", type=float, default=0.35)
    parser.add_argument("--device-name", default="Loop120 by Shokz")
    args = parser.parse_args()

    if args.seconds <= 0:
        parser.error("--seconds must be greater than zero")
    if not 0 < args.gain <= 1:
        parser.error("--gain must be greater than zero and at most one")

    try:
        input_index, input_info = find_device(args.device_name, "max_input_channels")
        output_index, output_info = find_device(args.device_name, "max_output_channels")
        sample_rate = choose_sample_rate(input_index, output_index)
    except (RuntimeError, sd.PortAudioError) as exc:
        print(f"[Loopback] ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"[Loopback] Input:  {input_info['name']} (device {input_index})")
    print(f"[Loopback] Output: {output_info['name']} (device {output_index})")
    print(
        f"[Loopback] Running {args.seconds:g}s at {sample_rate} Hz, "
        f"gain={args.gain:g}. Speak normally."
    )

    peak = 0.0

    def callback(indata, outdata, frames, timing, status) -> None:
        del frames, timing
        nonlocal peak
        if status:
            print(f"[Loopback] {status}", file=sys.stderr)
        mono = np.clip(indata[:, 0] * args.gain, -1.0, 1.0)
        peak = max(peak, float(np.max(np.abs(indata[:, 0]))))
        outdata[:, 0] = mono
        outdata[:, 1] = mono

    try:
        with sd.Stream(
            device=(input_index, output_index),
            samplerate=sample_rate,
            blocksize=512,
            channels=(1, 2),
            dtype="float32",
            latency="low",
            callback=callback,
        ):
            time.sleep(args.seconds)
    except (KeyboardInterrupt, sd.PortAudioError) as exc:
        if isinstance(exc, sd.PortAudioError):
            print(f"[Loopback] ERROR: {exc}", file=sys.stderr)
            return 1

    print(f"[Loopback] Complete. Input peak={peak:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
