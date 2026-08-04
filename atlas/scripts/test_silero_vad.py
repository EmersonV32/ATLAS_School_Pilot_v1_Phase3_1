#!/usr/bin/env python3
"""Load ATLAS's local Silero ONNX model and run one silent frame."""

from __future__ import annotations

import argparse

import numpy as np

from atlas.audio.silero_vad import SileroVAD


def main() -> None:
    parser = argparse.ArgumentParser(description="Test local Silero VAD")
    parser.add_argument("--model", default="models/silero_vad.onnx")
    args = parser.parse_args()

    vad = SileroVAD(model_path=args.model)
    vad.warm_up()
    silent_pcm = np.zeros(512, dtype="<i2").tobytes()
    probability = vad.probability(silent_pcm)
    print(f"Silero VAD ready: {args.model}")
    print(f"Silent-frame speech probability: {probability:.6f}")


if __name__ == "__main__":
    main()
