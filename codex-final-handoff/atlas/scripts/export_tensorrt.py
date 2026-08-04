"""Export the ATLAS YOLO model to a Jetson-specific TensorRT FP16 engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="models/atlas_yolo.pt")
    parser.add_argument("--imgsz", type=int, default=416)
    parser.add_argument("--workspace", type=float, default=2.0)
    args = parser.parse_args()

    jetpack_packages = Path("/usr/lib/python3.10/dist-packages")
    if jetpack_packages.is_dir():
        sys.path.append(str(jetpack_packages))

    from ultralytics import YOLO  # type: ignore

    model_path = Path(args.model)
    if not model_path.is_file():
        raise SystemExit(f"Model not found: {model_path}")

    output = YOLO(str(model_path)).export(
        format="engine",
        imgsz=args.imgsz,
        half=True,
        batch=1,
        device=0,
        workspace=args.workspace,
        simplify=False,
    )
    print(f"TensorRT engine ready: {output}")


if __name__ == "__main__":
    main()
