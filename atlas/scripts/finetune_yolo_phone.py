"""Fine-tune an ATLAS YOLO checkpoint for camera views of phone displays."""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=20)
    args = parser.parse_args()
    model = YOLO(str(args.model), task="detect")
    model.train(
        data=str(args.data),
        epochs=args.epochs,
        imgsz=416,
        batch=8,
        device=0,
        workers=2,
        patience=6,
        project=str(args.project),
        name="finetune",
        exist_ok=True,
        plots=False,
        cache=False,
        lr0=0.002,
        close_mosaic=5,
    )


if __name__ == "__main__":
    main()
