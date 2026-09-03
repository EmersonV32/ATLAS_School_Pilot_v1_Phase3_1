# ATLAS model recovery

`atlas_yolo.pt` is the authoritative portable artwork checkpoint committed for
fresh-OS recovery. The current file is the 2026-09-03 YOLO26 Nano seven-class
candidate returned from the team-authored `futureinnovators-v4` workflow.

| Artifact | Role | SHA-256 | Recovery policy |
|---|---|---|---|
| `atlas_yolo.pt` | Portable seven-class Ultralytics checkpoint | `6b86324bd641bfa629690d35c2c10f0dc7f4caed800db47d922ec3991543618a` | Committed |
| `atlas_yolo.onnx` | Intermediate export | Target-specific, pending regeneration | Regenerate |
| `atlas_yolo.engine` | TensorRT FP16 engine | Target-specific, pending regeneration | Regenerate on the Jetson |
| `silero_vad.onnx` | Local voice activity detector | `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3` | Download and verify |

The release evidence, training settings, curves, and held-out confusion matrix
are in `releases/2026-09-03-yolo26n-atlas-v4/`. The prior three-class production
checkpoint remains recoverable from Git commit `4db5086` until the new model
passes the physical-camera rehearsal.

TensorRT engines are coupled to the TensorRT, CUDA, and GPU stack. Never copy an
engine from another machine. The maintained deployment script removes a stale
engine, checks the checkpoint class order, and builds a new engine on the target
Jetson. For manual recovery, run:

```bash
./scripts/restore_models.sh
python scripts/verify_yolo_checkpoint.py
python scripts/export_tensorrt.py --model models/atlas_yolo.pt --imgsz 416
```

The nationals-era repository and its original detector remain under
`../../archive/2026-08-04-nationals-2026/`.
