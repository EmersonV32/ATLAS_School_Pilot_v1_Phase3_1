#!/usr/bin/env python3
"""Validate an ATLAS YOLO checkpoint against a prepared Ultralytics dataset."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--split", default="test", choices=("train", "val", "test"))
    parser.add_argument("--imgsz", default=416, type=int)
    parser.add_argument("--device", default="0")
    parser.add_argument("--batch", default=8, type=int)
    args = parser.parse_args()

    if args.model.suffix.lower() == ".engine":
        jetpack_packages = "/usr/lib/python3.10/dist-packages"
        if Path(jetpack_packages).is_dir() and jetpack_packages not in sys.path:
            sys.path.append(jetpack_packages)
    os.environ.setdefault("YOLO_AUTOINSTALL", "false")

    from ultralytics import YOLO

    metrics = YOLO(str(args.model), task="detect").val(
        data=str(args.data),
        split=args.split,
        imgsz=args.imgsz,
        device=args.device,
        batch=args.batch,
        plots=False,
        project="/tmp",
        name="atlas-yolo-diagnostic",
        exist_ok=True,
        verbose=False,
    )
    names = metrics.names
    class_maps = list(metrics.box.maps)
    report = {
        "model": str(args.model),
        "dataset": str(args.data),
        "split": args.split,
        "map50": round(float(metrics.box.map50), 6),
        "map50_95": round(float(metrics.box.map), 6),
        "precision": round(float(metrics.box.mp), 6),
        "recall": round(float(metrics.box.mr), 6),
        "per_class_map50_95": {
            str(names[index]): round(float(value), 6)
            for index, value in enumerate(class_maps)
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
