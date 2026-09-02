"""Fine-tune YOLO26 Nano and evaluate the saved checkpoint on ATLAS data."""

from __future__ import annotations

from pathlib import Path

from ultralytics import YOLO  # type: ignore


ROOT = Path(__file__).resolve().parent
DATA_YAML = ROOT / "datasets" / "atlas-artworks-v4" / "data.yaml"
RUNS_DIR = ROOT / "runs"
RUN_NAME = "yolo26n-atlas-v4"


def main() -> None:
    if not DATA_YAML.is_file():
        raise FileNotFoundError(
            f"Prepared dataset missing: {DATA_YAML}. Run prepare_artwork_dataset.py first."
        )

    model = YOLO("yolo26n.pt")
    model.train(
        data=str(DATA_YAML),
        epochs=100,
        imgsz=640,
        batch=-1,
        patience=20,
        workers=4,
        project=str(RUNS_DIR),
        name=RUN_NAME,
        exist_ok=True,
        plots=True,
        save=True,
    )

    best_model = YOLO(RUNS_DIR / RUN_NAME / "weights" / "best.pt")
    metrics = best_model.val(
        data=str(DATA_YAML),
        split="test",
        imgsz=640,
        project=str(RUNS_DIR),
        name=f"{RUN_NAME}-test",
        exist_ok=True,
        plots=True,
    )
    print(f"Test mAP50: {metrics.box.map50:.4f}")
    print(f"Test mAP50-95: {metrics.box.map:.4f}")
    print(f"Best checkpoint: {RUNS_DIR / RUN_NAME / 'weights' / 'best.pt'}")


if __name__ == "__main__":
    main()
