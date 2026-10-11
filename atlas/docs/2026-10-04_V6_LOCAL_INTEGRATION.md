# V6 local integration — October 4, 2026

Later user-approved Jetson deployment is recorded in
[`2026-10-04_JETSON_V6_DEPLOYMENT.md`](2026-10-04_JETSON_V6_DEPLOYMENT.md).
V6 is now running on that device. This document records the earlier local stage.

Branch: `codex/v6-model-handoff-2026-10-04`. The user explicitly requested
integration after the five-fix/model-preparation task. Changes remain local;
no commit, push, main merge, physical deployment or Jetson package changes.

## Active model and rollback

`models/atlas_yolo.pt` now contains the exact mentor ZIP's v6 `best.pt`:

`af11b2de376a5c54a1ee11e9765f91ecbf54a1f308a2a82f9106b00a78409731`

`models/manifest.sha256` matches. The exact previous model is preserved under
`models/releases/2026-09-07-camera-domain-rollback/atlas_yolo.pt` with its
original SHA-256:

`5680d3a5fff21d482e579c47f0b19e030b6acbdefdfe5da188de9cc961a66bec`

The seven embedded numeric classes agree with `config/artwork_labels.yaml` and
the seven-artwork, 157-chunk content pack. Input size remains 416; confidence,
mask-specific confidence, centering, orientation and stability settings are
unchanged. Mock dev/demo mode stays mock. The new `yolo_device` setting defaults
to the existing Jetson GPU 0; `ATLAS_YOLO_DEVICE=cpu` permits CPU checks.

## Stale TensorRT protection

An existing old engine previously won `auto` selection merely by existing.
The target exporter now records a generated `.engine.manifest.json` containing
checkpoint SHA-256, engine SHA-256 and input size. Both `auto` and `tensorrt`
use an engine only when all three match, otherwise warning/falling back to the
current PT. Legacy engines need re-export. Load/predict failure of a matching
engine retains the existing PT fallback. No model or engine is deleted by
runtime selection. The transactional deploy backup/rollback now includes the
sidecar; portable bundles never ship generated engines or sidecars.

## Real inference evidence

A separate, ignored `.venv-yolo` was created; the existing `.venv` and physical
Jetson stack were not altered. It used Python 3.12.13, Ultralytics **8.4.115**,
PyTorch **2.8.0+cpu**, torchvision **0.23.0+cpu**, NumPy 1.26.4 and OpenCV 4.10.
These ML versions match the recorded Jetson lock's library versions, but this
Windows CPU result does not establish ARM/CUDA/TensorRT compatibility.

The checkpoint was first loaded/tested at the candidate path before activation.
The canonical active path was then tested again through `Container`'s real
device-mode `YoloDetector` and `ArtworkTracker`, without opening any camera,
microphone, EV3, cloud client, visitor log or existing runtime database.

At 416, approved public reference assets in `artwork-source/` produced:

- Mona Lisa: correct `mona_lisa`, confidence 0.873686, stable after three frames.
- The Great Wave: correct `great_wave_off_kanagawa`, confidence 0.857227, stable
  after three frames.
- Black blank frame: no detection; resetting the tracker left no stale context.

Normalized boxes were in bounds. These two public references are **functional
smoke fixtures**, not independent camera holdouts. All seven ID mappings also
have hardware-free regression coverage; this is not a seven-class live accuracy
measurement. The mentor's test-split mAP was not rerun or used to tune thresholds.

## Regression and recovery gate

- Full normal laptop suite: **2,984 passed, 1 skipped** in 148.67 seconds. The
  skipped case is the explicitly opt-in real-inference check; one existing
  Starlette/httpx deprecation warning remains.
- Separate CPU ML environment, with real inference enabled: **28 passed** in
  17.06 seconds, including the canonical active-model smoke check.
- Final model packaging/metadata/rollback regressions: **48 passed, 1 skipped**,
  including all 13 transactional deployment scenarios after sidecar changes.
- All 65 focused device/content/integration checks passed before activation.
- Changed-file Ruff, secret scan, recovery-bundle verifier, strict content
  contract (7 artworks / 157 chunks), active checksum, supplied-ZIP match,
  Python compilation, Bash/admin-JavaScript syntax and `git diff --check` passed.
  Repository-wide Ruff's earlier unrelated violations were not rewritten.

The five previous runtime fixes remain in the full regression gate. No visitor
UI assets/flow changed during this integration; the earlier mock keyboard/
1024x768 visitor validation remains applicable. Physical iPad testing and live
reduced-motion emulation remain unverified, as recorded in the five-fix report.
The metadata-only ZIP inspector deliberately does not claim inference; the
separate runtime smoke check supplies the actual inference evidence.

## Repeat the smoke check

From `atlas/`, use a separate environment (never run these CPU installation
commands on the protected Jetson):

```powershell
python -m venv .venv-yolo
./.venv-yolo/Scripts/python.exe -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu
./.venv-yolo/Scripts/python.exe -m pip install -r requirements-yolo-cpu.txt
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:YOLO_CONFIG_DIR = Join-Path (Resolve-Path '..').Path '.tools/yolo-smoke'
$env:MPLCONFIGDIR = Join-Path $env:YOLO_CONFIG_DIR 'matplotlib'
New-Item -ItemType Directory -Force (Join-Path $env:YOLO_CONFIG_DIR 'Ultralytics'), $env:MPLCONFIGDIR | Out-Null
$env:YOLO_OFFLINE = 'true'
./.venv-yolo/Scripts/python.exe scripts/verify_yolo_checkpoint.py
./.venv-yolo/Scripts/python.exe scripts/smoke_yolo_runtime.py --device cpu --imgsz 416
$env:ATLAS_TEST_REAL_YOLO = '1'
./.venv-yolo/Scripts/python.exe -m pytest tests/test_yolo_model_integration.py -p no:cacheprovider -q
```

Do not recreate an already existing environment; the installation lines are
for a fresh setup. The official version-pair command is documented by
[PyTorch](https://pytorch.org/get-started/previous-versions/); YOLO installation
is documented by [Ultralytics](https://docs.ultralytics.com/quickstart/).

## Remaining physical release gates

Explicit approval is still required to deploy or test on the Jetson. Before
live promotion, evaluate new session-separated XIAO frames for all seven works
and unrelated scenes against predeclared miss/false-alarm limits. Then export
a new FP16 engine on that Jetson at 416, compare PT/TRT class IDs and boxes on
the same frames, and measure sustained thermals and end-to-end latency.
The returned mentor archive contains no fresh independent camera holdout.
