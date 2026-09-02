"""Train and evaluate the ATLAS YOLO26 Nano artwork detector."""

from __future__ import annotations

from pathlib import Path

from ultralytics import YOLO


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset" / "data.yaml"
RUNS = ROOT / "runs"
RUN_NAME = "yolo26n-atlas-v4"


def main() -> None:
    if not DATASET.is_file():
        raise FileNotFoundError(f"Missing dataset config: {DATASET}")

    model = YOLO("yolo26n.pt")
    model.train(
        data=str(DATASET),
        epochs=100,
        imgsz=640,
        batch=-1,
        patience=20,
        workers=4,
        project=str(RUNS),
        name=RUN_NAME,
        exist_ok=True,
        plots=True,
        save=True,
    )

    best = YOLO(RUNS / RUN_NAME / "weights" / "best.pt")
    metrics = best.val(
        data=str(DATASET),
        split="test",
        imgsz=640,
        project=str(RUNS),
        name=f"{RUN_NAME}-test",
        exist_ok=True,
        plots=True,
    )
    print(f"Test mAP50: {metrics.box.map50:.4f}")
    print(f"Test mAP50-95: {metrics.box.map:.4f}")


if __name__ == "__main__":
    main()
