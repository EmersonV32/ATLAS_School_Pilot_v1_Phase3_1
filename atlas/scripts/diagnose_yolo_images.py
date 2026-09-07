#!/usr/bin/env python3
"""Compare raw YOLO predictions across models on the same images."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _ordered_names(names: Any) -> list[str]:
    if isinstance(names, dict):
        return [str(names[key]) for key in sorted(names, key=int)]
    return [str(name) for name in names]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument(
        "--models",
        nargs="+",
        type=Path,
        default=[Path("models/atlas_yolo.pt"), Path("models/atlas_yolo.engine")],
    )
    parser.add_argument("--imgsz", type=int, default=416)
    parser.add_argument("--conf", type=float, default=0.01)
    args = parser.parse_args()

    jetpack_packages = Path("/usr/lib/python3.10/dist-packages")
    if jetpack_packages.is_dir():
        sys.path.append(str(jetpack_packages))

    from ultralytics import YOLO  # type: ignore

    missing = [str(path) for path in (*args.models, *args.images) if not path.is_file()]
    if missing:
        print(json.dumps({"error": "missing files", "paths": missing}, indent=2))
        return 2

    report: dict[str, Any] = {"imgsz": args.imgsz, "conf": args.conf, "models": {}}
    for model_path in args.models:
        model = YOLO(str(model_path), task="detect")
        model_report: dict[str, Any] = {
            "names": _ordered_names(model.names),
            "images": {},
        }
        for image_path in args.images:
            result = model.predict(
                str(image_path),
                imgsz=args.imgsz,
                conf=args.conf,
                device=0,
                verbose=False,
            )[0]
            predictions = []
            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    predictions.append(
                        {
                            "class_id": class_id,
                            "label": str(result.names[class_id]),
                            "confidence": round(float(box.conf[0]), 6),
                            "xyxyn": [round(float(value), 6) for value in box.xyxyn[0]],
                        }
                    )
            predictions.sort(key=lambda item: item["confidence"], reverse=True)
            model_report["images"][image_path.name] = predictions
        report["models"][str(model_path)] = model_report

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
