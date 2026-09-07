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

For the camera-generalization retrain, rebuild the dataset by reviewed capture
ranges, then add synthetic XIAO-style phone scenes generated only from training
crops:

```powershell
python training/prepare_artwork_dataset_v5.py
python scripts/build_phone_yolo_dataset.py `
  --source training/datasets/atlas-artworks-v5-base `
  --output training/datasets/atlas-artworks-v5 `
  --samples-per-class 180
```

The v5 preparation intentionally excludes a buffer between validation and test
ranges. Its `split_manifest.json` records every assignment and class count.

## Training

Install the vision extra in an environment with a CUDA-capable NVIDIA GPU:

```powershell
pip install -e ".[vision]"
python training/train_artwork_detector.py
```

The current handoff run starts from untouched `yolo26n.pt` at 640px and writes
results under `runs/yolo26n-atlas-v5-camera/`. Starting from the v4 ATLAS
checkpoint would contaminate the new test because that checkpoint saw the old
random split. The script evaluates `best.pt` on the locked test at both 640px
and production 416px.

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
