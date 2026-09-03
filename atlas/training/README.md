# Artwork detector training

This directory contains the reproducible training workflow for the current
ATLAS artwork detector. Dataset images and generated checkpoints are ignored by
Git; only the scripts and class contract are versioned.

## Dataset preparation

Extract the Roboflow YOLOv8 export to:

```text
training/datasets/futureinnovators-v4/
```

Then run:

```powershell
python training/prepare_artwork_dataset.py
```

The script checks that every source label maps to an ATLAS artwork ID and
writes `training/datasets/atlas-artworks-v4/data.yaml` without modifying the
original Roboflow export.

## Training

Install the vision extra in an environment with a CUDA-capable NVIDIA GPU:

```powershell
pip install -e ".[vision]"
python training/train_artwork_detector.py
```

The default run fine-tunes `yolo26n.pt` at 640px and writes results under
`training/runs/yolo26n-atlas-v4/`. It also evaluates the saved `best.pt` on the
held-out test split.

## Release gate

Do not replace `models/atlas_yolo.pt` until the trained model has passed:

1. `scripts/validate_artwork_release.py` using the prepared `data.yaml`.
2. A physical-camera test set that was not used in the Roboflow export.
3. The Jetson PyTorch versus TensorRT benchmark.

The TensorRT engine must be built on the Jetson. Keep the current `atlas_yolo.pt`
until a full demo rehearsal succeeds.

## 2026-09-03 returned checkpoint

The returned YOLO26 Nano checkpoint and evidence passed the repository class
contract and dataset split-integrity checks. It is staged as
`models/atlas_yolo.pt`; see
`models/releases/2026-09-03-yolo26n-atlas-v4/README.md` for metrics, hashes, and
the remaining physical-camera and Jetson release gates.
