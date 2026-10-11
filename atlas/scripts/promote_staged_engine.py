"""Promote an engine built and verified in this Jetson's staging directory."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from atlas.vision.artwork_release import load_model_labels
from atlas.vision.model_artifacts import (
    engine_manifest_path,
    engine_matches_checkpoint,
    sha256_file,
)
from atlas.vision.yolo_detector import YoloDetector

ROOT = Path(__file__).resolve().parents[1]


def promote_staged_engine(
    staged_root: Path, checkpoint: Path, image_size: int
) -> Path:
    staged_checkpoint = staged_root / "models/atlas_yolo.pt"
    staged_engine = staged_root / "models/atlas_yolo.engine"
    for artifact in (
        staged_checkpoint, staged_engine, engine_manifest_path(staged_engine)
    ):
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError(
                "Staged model artifacts must be regular, non-symlink files"
            )
    if sha256_file(staged_checkpoint) != sha256_file(checkpoint):
        raise ValueError("Staged checkpoint differs from the model being deployed")
    if not engine_matches_checkpoint(staged_checkpoint, staged_engine, image_size):
        raise ValueError(
            "Staged engine provenance does not match checkpoint/input size"
        )
    destination = checkpoint.with_suffix(".engine")
    shutil.copy2(staged_engine, destination)
    shutil.copy2(engine_manifest_path(staged_engine), engine_manifest_path(destination))
    if not engine_matches_checkpoint(checkpoint, destination, image_size):
        raise ValueError("Promoted engine did not pass the destination checksum check")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged-root", required=True)
    parser.add_argument("--model", default="models/atlas_yolo.pt")
    parser.add_argument("--imgsz", type=int, default=416)
    args = parser.parse_args()
    staged = Path(args.staged_root).resolve(strict=True)
    if staged.parent != Path("/tmp") or not staged.name.startswith(
        "atlas_v6_preflight_"
    ):
        raise ValueError(
            "Expected this Jetson's explicit /tmp/atlas_v6_preflight_* root"
        )
    checkpoint = Path(args.model)
    engine = promote_staged_engine(staged, checkpoint, args.imgsz)
    # Verify the copied artifact on this GPU, without silently falling back to PT.
    detector = YoloDetector(str(engine), image_size=args.imgsz, device=0)
    detector.warm_up()
    if detector.class_names != load_model_labels(ROOT / "config/artwork_labels.yaml"):
        raise ValueError("Promoted TensorRT engine class order does not match ATLAS")
    print(json.dumps({
        "staged_engine_verified": True,
        "checkpoint_sha256": sha256_file(checkpoint),
        "engine_sha256": sha256_file(engine),
        "image_size": args.imgsz,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
