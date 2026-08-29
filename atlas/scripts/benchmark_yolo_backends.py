"""Compare ATLAS PyTorch and TensorRT YOLO latency on the Jetson camera."""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import cv2  # type: ignore


def _capture_frames(source: str, count: int) -> list[Any]:
    parsed_source: str | int = int(source) if source.isdigit() else source
    capture = cv2.VideoCapture(parsed_source)
    frames: list[Any] = []
    try:
        deadline = time.monotonic() + 15.0
        while len(frames) < count and time.monotonic() < deadline:
            ok, frame = capture.read()
            if ok and frame is not None:
                frames.append(frame)
    finally:
        capture.release()
    if not frames:
        raise RuntimeError(f"No frames received from {source}")
    return frames


def _load_images(paths: list[str]) -> list[Any]:
    frames = []
    for path in paths:
        frame = cv2.imread(path)
        if frame is None:
            raise RuntimeError(f"Could not read image: {path}")
        frames.append(frame)
    return frames


def _benchmark(model_path: str, frames: list[Any], imgsz: int) -> dict[str, Any]:
    from ultralytics import YOLO  # type: ignore

    model = YOLO(model_path, task="detect")
    for _ in range(3):
        model.predict(frames[0], imgsz=imgsz, device=0, verbose=False)

    wall_ms: list[float] = []
    inference_ms: list[float] = []
    detections = 0
    class_counts: Counter[str] = Counter()
    for frame in frames:
        started = time.perf_counter()
        results = model.predict(frame, imgsz=imgsz, device=0, verbose=False)
        wall_ms.append((time.perf_counter() - started) * 1000.0)
        inference_ms.extend(float(result.speed["inference"]) for result in results)
        detections += sum(len(result.boxes) for result in results)
        for result in results:
            for class_id in result.boxes.cls.tolist():
                class_counts[str(result.names[int(class_id)])] += 1
    return {
        "median_wall_ms": statistics.median(wall_ms),
        "p95_wall_ms": sorted(wall_ms)[max(0, int(len(wall_ms) * 0.95) - 1)],
        "median_inference_ms": statistics.median(inference_ms),
        "detections": detections,
        "class_counts": dict(class_counts),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="http://atlas-camera.local:81/stream")
    parser.add_argument("--pytorch", default="models/atlas_yolo.pt")
    parser.add_argument("--engine", default="models/atlas_yolo.engine")
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--imgsz", type=int, default=416)
    parser.add_argument("--images", nargs="*", default=[])
    args = parser.parse_args()

    jetpack_packages = Path("/usr/lib/python3.10/dist-packages")
    if jetpack_packages.is_dir():
        sys.path.append(str(jetpack_packages))

    frames = _load_images(args.images) if args.images else _capture_frames(
        args.source, args.frames
    )
    pytorch = _benchmark(args.pytorch, frames, args.imgsz)
    engine = _benchmark(args.engine, frames, args.imgsz)
    speedup = pytorch["median_wall_ms"] / engine["median_wall_ms"]
    print(f"Frames: {len(frames)}")
    print(f"PyTorch: {pytorch}")
    print(f"TensorRT: {engine}")
    print(f"Median end-to-end speedup: {speedup:.2f}x")


if __name__ == "__main__":
    main()
