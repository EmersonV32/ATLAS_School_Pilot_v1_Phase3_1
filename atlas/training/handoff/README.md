# ATLAS artwork detector v5 camera training handoff

This package contains a leakage-resistant split of the existing ATLAS artwork
dataset plus camera-style synthetic training scenes. No new photographs are
required for this experiment. It is intended for a CUDA-capable computer.

The split is deliberate: neighboring phone captures are kept together, and a
buffer is omitted between the validation and locked test ranges. Synthetic
images exist only in `train`; do not reshuffle the package.

## Train

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python train.py
```

The script starts from the untouched pretrained `yolo26n.pt` model at 640px for
up to 100 epochs with early stopping. Do not initialize this run from the old
ATLAS v4 checkpoint: that checkpoint already saw images now reserved for the
locked test. The script automatically chooses the largest safe batch size and
tests the result at both 640px and ATLAS's production 416px input size.

## Return these files

After training, send back:

```text
runs/yolo26n-atlas-v5-camera/weights/best.pt
runs/yolo26n-atlas-v5-camera/results.csv
runs/yolo26n-atlas-v5-camera/atlas_evaluation.json
runs/yolo26n-atlas-v5-camera-test-416/
```

`best.pt` is the required file. The metrics and test results let ATLAS verify
the model before putting it on the Jetson.

## Class contract

The numeric class order must not change:

```text
0 girl_with_a_pearl_earring
1 great_wave_off_kanagawa
2 liberty_leading_the_people
3 mona_lisa
4 tutankhamun_mask
5 starry_night
6 sunflowers
```

Do not rename, reorder, remove, or merge these classes. Do not send a TensorRT
engine: ATLAS will build that engine on its own Jetson.

## Acceptance rule

The candidate is not deployment-ready merely because its mAP is high. Return
the complete run so ATLAS can check every class on the locked capture ranges,
then compare PyTorch and TensorRT on the Jetson and physically show all seven
artworks to the XIAO camera.
