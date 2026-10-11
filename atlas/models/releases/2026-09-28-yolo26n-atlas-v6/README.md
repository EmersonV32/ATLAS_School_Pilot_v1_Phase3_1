# ATLAS v6 YOLO26 Nano — deployed prototype

Later October 4 update: the user explicitly approved Jetson deployment. V6 is
now running with a new on-device FP16 engine at 416; native regression and public
reference PT/TRT checks passed. See
`../../../docs/2026-10-04_JETSON_V6_DEPLOYMENT.md`. Fresh seven-class camera,
spoken end-to-end and sustained thermal acceptance remain unverified.
The local-only paragraph below records the prior integration stage.

This is the trained model returned by the coach on 2026-09-28, plus the evidence needed for a new developer/chat to continue. On October 4 the user explicitly requested local integration: the same bytes now occupy `../../atlas_yolo.pt`, and the previous checkpoint is preserved for rollback. It remains a **physical-release candidate**, not a Jetson deployment. Fresh XIAO-camera footage and target-device tests must pass before live promotion.

The real loader and ATLAS detector/tracker passed CPU smoke inference at 416
with Ultralytics 8.4.115 and PyTorch 2.8.0+cpu. Both public Mona Lisa/Great Wave
references were correctly recognized, and a blank frame had no detection.
This verifies a functional path, not independent accuracy or CUDA/TensorRT
compatibility. See `../../../docs/2026-10-04_V6_LOCAL_INTEGRATION.md`.

## Verified artifact

- `best.pt`: SHA-256 `af11b2de376a5c54a1ee11e9765f91ecbf54a1f308a2a82f9106b00a78409731`; this matches `atlas_evaluation.json`. At initial preparation it was only ZIP-inspected; the October 4 local integration additionally loaded it and ran real CPU inference.
- PyTorch checkpoints can contain executable pickle data. Treat this externally trained file as untrusted until provenance is accepted; load/test it first in an isolated environment, not on the live Jetson.
- Architecture: YOLO26 Nano initialized from official `yolo26n.pt`.
- Trainer report: Ultralytics 8.4.163, Python 3.12.3, CUDA PyTorch 2.12.0+cu126, NVIDIA GeForce RTX 3070 Laptop GPU.
- The run recorded 45 epochs. The highest validation mAP50–95 in `results.csv` was 0.80279 at epoch 25; the saved `best.pt` was evaluated on the test split after training.
- Prepared data: 989 train, 324 validation, 233 test images; 1,546 total. Test has 343 labeled boxes and 22 negative images. Images themselves are **not in Git**.

## Test results from `atlas_evaluation.json`

| Evaluation input | mAP50 | mAP50–95 | Mona Lisa mAP50–95 |
| --- | ---: | ---: | ---: |
| 640 | 0.9702 | 0.7977 | 0.6138 |
| 416 | 0.9649 | 0.7887 | 0.5732 |

The overall averages were recomputed from the seven per-class AP values. These are detection metrics on the prepared split, not live recognition accuracy. The 416 evaluation reuses the **same checkpoint**; it is not a second training run. Mona Lisa is the weakest class by the stricter metric at 416. The confusion plots also show extra detections against background, so check false alarms on new unrelated art.

## Included files

- `atlas_evaluation.json`, `class_results.csv`, `results.csv`: full metrics and training history.
- `training_results.png`, test confusion matrices, `test_416_precision_recall.png`: visual evidence.
- `DATASET_REVIEW.md`, `dataset_preparation.json`, `dataset_manifest.json`: data decisions, counts, exclusions, source IDs and hashes; no raw photos.
- `train.py`, `requirements.txt`: exact coach-side training recipe returned with the results.

The source Roboflow v6 ZIP is not in Git. Its SHA-256 is `47d1021c3f77f06a3d252617cc1bf8241b964d5dc29e2b2f9f9cdfb377266a88`. `DATASET_REVIEW.md` explains why split leakage risk was reduced but not eliminated. The local user workspace may also have the original source, prepared coach package and complete returned results ZIP; do not assume those files exist on another machine.

## Next gate

1. Test `best.pt` against **new** footage from the actual Seeed XIAO ESP32-S3 Sense at headset height. Include all seven artworks, different lighting/angles/distances, partial views, movement and unrelated art. Record misses and false alarms with a predeclared acceptance threshold.
2. Confirm numeric class order and compare `.pt` predictions with a newly built TensorRT engine on the target Jetson at 416. Do not transfer the coach computer's engine or reuse an old one.
3. Measure end-to-end camera-to-response latency and sustained thermals on the physical hardware, then decide whether to promote this checkpoint. Preserve rollback to the current model.

No physical-camera or Jetson validation of this v6 candidate is recorded here.
