# ATLAS artwork detector training handoff

This package contains the ATLAS artwork dataset version 4, already converted
to the class IDs expected by the runtime. It is intended for a CUDA-capable
computer.

## Train

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python train.py
```

The script fine-tunes `yolo26n.pt` at 640px for up to 100 epochs with early
stopping. It automatically chooses the largest safe batch size.

## Return these files

After training, send back:

```text
runs/yolo26n-atlas-v4/weights/best.pt
runs/yolo26n-atlas-v4/results.csv
runs/yolo26n-atlas-v4/confusion_matrix.png
runs/yolo26n-atlas-v4-test/
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
