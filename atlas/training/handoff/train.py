"""Fine-tune and evaluate the ATLAS v5 artwork detector candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset" / "data.yaml"
RUNS = ROOT / "runs"
RUN_NAME = "yolo26n-atlas-v5-camera"
TRAINING_OVERRIDES: dict[str, float] = {
    "hsv_h": 0.01,
    "hsv_s": 0.45,
    "hsv_v": 0.45,
    "degrees": 12.0,
    "translate": 0.15,
    "scale": 0.45,
    "shear": 3.0,
    "perspective": 0.0008,
    "flipud": 0.0,
    "fliplr": 0.0,
    "mosaic": 0.35,
    "mixup": 0.05,
    "erasing": 0.2,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="yolo26n.pt",
        help="Base model; keep yolo26n.pt for an uncontaminated test",
    )
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--device", default=None)
    parser.add_argument("--physical-data", type=Path)
    return parser.parse_args()


def summarize(metrics: Any) -> dict[str, Any]:
    names = metrics.names
    ap50 = list(metrics.box.ap50)
    return {
        "map50": round(float(metrics.box.map50), 6),
        "map50_95": round(float(metrics.box.map), 6),
        "precision": round(float(metrics.box.mp), 6),
        "recall": round(float(metrics.box.mr), 6),
        "per_class_ap50": {
            str(names[index]): round(float(value), 6)
            for index, value in enumerate(ap50)
        },
    }


def evaluate(model: Any, data: Path, split: str, imgsz: int, name: str) -> Any:
    return model.val(
        data=str(data),
        split=split,
        imgsz=imgsz,
        project=str(RUNS),
        name=name,
        exist_ok=True,
        plots=True,
    )


def main() -> None:
    args = parse_args()
    if not DATASET.is_file():
        raise FileNotFoundError(f"Missing dataset config: {DATASET}")
    if args.physical_data and not args.physical_data.is_file():
        raise FileNotFoundError(f"Missing physical-camera data: {args.physical_data}")

    from ultralytics import YOLO

    model = YOLO(args.model, task="detect")
    training_args: dict[str, Any] = {
        "data": str(DATASET),
        "epochs": args.epochs,
        "imgsz": 640,
        "batch": -1,
        "patience": 20,
        "workers": 4,
        "project": str(RUNS),
        "name": RUN_NAME,
        "exist_ok": True,
        "plots": True,
        "save": True,
        "cache": False,
        "close_mosaic": 8,
        "cos_lr": True,
        **TRAINING_OVERRIDES,
    }
    if args.device is not None:
        training_args["device"] = args.device
    model.train(**training_args)

    best_path = RUNS / RUN_NAME / "weights" / "best.pt"
    best = YOLO(best_path, task="detect")
    report: dict[str, Any] = {
        "checkpoint": str(best_path),
        "starting_checkpoint": args.model,
        "locked_test_640": summarize(
            evaluate(best, DATASET, "test", 640, f"{RUN_NAME}-test-640")
        ),
        "locked_test_production_416": summarize(
            evaluate(best, DATASET, "test", 416, f"{RUN_NAME}-test-416")
        ),
    }
    if args.physical_data:
        report["physical_camera_416"] = summarize(
            evaluate(
                best,
                args.physical_data.resolve(),
                "test",
                416,
                f"{RUN_NAME}-physical-416",
            )
        )
    report_path = RUNS / RUN_NAME / "atlas_evaluation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Best checkpoint: {best_path}")
    print(f"Evaluation report: {report_path}")


if __name__ == "__main__":
    main()
