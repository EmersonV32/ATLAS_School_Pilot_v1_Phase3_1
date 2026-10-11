# ATLAS model recovery

Latest state: **v6 was deployed to the Jetson on October 4 at 18:38 EDT**, after
explicit user approval, native tests and on-device PT/TensorRT reference checks.
The newly exported FP16 engine at 416 is bound to the active checkpoint. The
original weights/engine/config are preserved in a durable device backup. See
[`../docs/2026-10-04_JETSON_V6_DEPLOYMENT.md`](../docs/2026-10-04_JETSON_V6_DEPLOYMENT.md).
Fresh seven-class camera/voice/thermal acceptance checks still remain due.

`main` now preserves the mentor's exact **v6** checkpoint and matching
manifest. October 4 local CPU integration preceded the later Jetson deployment
above; it is not an alternative current state. Fresh XIAO-camera accuracy,
spoken end-to-end and sustained thermal acceptance remain required.

`atlas_yolo.pt` is the authoritative Git-tracked portable artwork path for
fresh-OS recovery. The current file is the returned YOLO26 Nano seven-class v6
checkpoint. Its evidence is in
[`releases/2026-09-28-yolo26n-atlas-v6/`](releases/2026-09-28-yolo26n-atlas-v6/).
The exact previous seven-class weights and checksum are preserved in
[`releases/2026-09-07-camera-domain-rollback/`](releases/2026-09-07-camera-domain-rollback/).

| Artifact | Role | SHA-256 | Recovery policy |
|---|---|---|---|
| `atlas_yolo.pt` | Portable seven-class v6 checkpoint | `af11b2de376a5c54a1ee11e9765f91ecbf54a1f308a2a82f9106b00a78409731` | Git-tracked recovery source |
| `atlas_yolo.onnx` | Intermediate export | Target-specific; excluded from Git | Regenerate during target rebuild |
| `atlas_yolo.engine` | TensorRT FP16 engine | Target-specific; October 4 device hash in deployment record | Regenerate on the target Jetson, never transfer across machines |
| `silero_vad.onnx` | Local voice activity detector | `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3` | Download and verify |

The original seven-class release evidence, training settings, curves, and
held-out confusion matrix are in `releases/2026-09-03-yolo26n-atlas-v4/`. The
prior three-class production checkpoint remains recoverable from Git commit
`4db5086` until the new model passes the physical-camera rehearsal.

TensorRT engines are coupled to the TensorRT, CUDA, and GPU stack. Never copy an
engine from another machine. The maintained deployment script removes a stale
engine, checks the checkpoint class order, and builds a new engine on the target
Jetson. For manual recovery, run:

```bash
./scripts/restore_models.sh
python scripts/verify_yolo_checkpoint.py
python scripts/export_tensorrt.py --model models/atlas_yolo.pt --imgsz 416
```

The exporter generates `atlas_yolo.engine.manifest.json`, binding checkpoint
SHA-256, engine SHA-256 and input size. `auto` and `tensorrt` selection refuse
unbound/stale engines and use the current PT instead. A legacy engine therefore
requires re-export; a matching engine that fails to load/predict still falls
back to the current PT. Generated engine sidecars are excluded from Git.

For a hardware-free **real** smoke check, see
[`../docs/2026-10-04_V6_LOCAL_INTEGRATION.md`](../docs/2026-10-04_V6_LOCAL_INTEGRATION.md).
Dev/demo mode deliberately continues to use `MockDetector`; changing weights
does not enable cameras, speech providers, servos or EV3 on a laptop.

The nationals-era dataset, training evidence and original detectors remain under
`../../archive/2026-08-04-nationals-2026/`; its obsolete runtime was retired.
See [the archive index](../../archive/README.md). Versioned checkpoints and
training/release recipes are intentionally retained for provenance and rollback,
not treated as unused application clutter.
