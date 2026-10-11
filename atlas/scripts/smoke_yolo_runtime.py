"""Check real ATLAS inference without cameras, cloud, audio, logs or visitor data.

Only approved public artwork assets are used, in memory. This is a functional
smoke check, NOT an independent accuracy benchmark or a hardware release gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from atlas.app.dependency_container import Container
from atlas.config.settings import HardwareSettings, PathsSettings, Settings
from atlas.models.enums import RunMode
from atlas.vision.artwork_release import load_model_labels, validate_artwork_release
from atlas.vision.model_artifacts import sha256_file

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_REFERENCES = (
    ("mona-lisa.png", "mona_lisa"),
    ("great-wave.png", "great_wave_off_kanagawa"),
)


def run_smoke_check(
    model: str | Path = ROOT / "models/atlas_yolo.pt",
    *,
    device: str = "cpu",
    image_size: int = 416,
) -> dict:
    import cv2
    import numpy as np
    import torch
    import ultralytics

    labels = ROOT / "config/artwork_labels.yaml"
    release = validate_artwork_release(
        ROOT / "data/content_packs/demo_pack",
        labels,
        require_all_content_detectable=True,
    )
    if not release.valid:
        raise ValueError("Model/content contract failed: " + "; ".join(release.errors))
    container = Container(
        Settings(
            mode=RunMode.DEVICE,
            paths=PathsSettings(content_packs_dir=ROOT / "data/content_packs"),
            hardware=HardwareSettings(
                yolo_model_path=str(model),
                yolo_backend="pytorch",
                yolo_device=device,
                yolo_imgsz=image_size,
            ),
        )
    )
    detector = container.vision_detector
    detector.warm_up()
    if detector.class_names != load_model_labels(labels):
        raise ValueError("Loaded checkpoint numeric class order does not match ATLAS")
    blank = np.zeros((image_size, image_size, 3), dtype=np.uint8)
    blank_detection = detector.detect(blank)
    checks = []
    tracker = container.artwork_tracker
    for filename, expected_id in PUBLIC_REFERENCES:
        # Public, curated source assets, not raw camera/visitor images.
        frame = cv2.imread(str(ROOT / "artwork-source" / filename))
        if frame is None:
            raise ValueError(f"Missing approved public artwork asset: {filename}")
        tracker.reset()
        detection = None
        for _ in range(3):
            detection = tracker.update(frame)
        check = {
            "public_reference": filename,
            "expected_id": expected_id,
            "actual_id": detection.artwork_id if detection else None,
            "confidence": detection.confidence if detection else None,
            "stable": bool(detection and detection.stable),
            "valid": bool(
                detection
                and detection.artwork_id == expected_id
                and detection.stable
                and all(0.0 <= coordinate <= 1.0 for coordinate in detection.bbox)
            ),
        }
        checks.append(check)
        tracker.reset()
        if tracker.update(blank) is not None:
            raise ValueError("A reset tracker retained context on a blank frame")
    return {
        "valid": blank_detection is None and all(check["valid"] for check in checks),
        "checkpoint_sha256": sha256_file(model),
        "active_model_path": detector.active_model_path,
        "class_names": detector.class_names,
        "image_size": image_size,
        "device": device,
        "ultralytics": ultralytics.__version__,
        "torch": torch.__version__,
        "blank_has_detection": blank_detection is not None,
        "public_reference_checks": checks,
        "physical_camera_validated": False,
        "tensorrt_validated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=str(ROOT / "models/atlas_yolo.pt"))
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--imgsz", type=int, default=416)
    args = parser.parse_args()
    report = run_smoke_check(args.model, device=args.device, image_size=args.imgsz)
    print(json.dumps(report, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
