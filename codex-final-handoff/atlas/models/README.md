# ATLAS model recovery

`atlas_yolo.pt` is the authoritative, portable artwork detector checkpoint.
It is committed because it is required to rebuild ATLAS after a fresh flash.

Verified artifacts from the working Jetson on 2026-08-04:

| Artifact | Role | SHA-256 | Recovery policy |
|---|---|---|---|
| `atlas_yolo.pt` | Portable Ultralytics/YOLO checkpoint | `53f4438df7af6b19550cd0b508e8cde84b2e1cfdc66296564516222aca4dbc0d` | Committed |
| `atlas_yolo.onnx` | Intermediate export | `f00ef8c174fbd30c16a31dba8ee5cb8f78ff91d87cbe4aa62587b4ead780025e` | Regenerate |
| `atlas_yolo.engine` | TensorRT 10.3 FP16 engine | `fd8e5aa9b539d12624a13c265b4378c43942ec546d59b9fc1d3acd526476afe8` | Regenerate on the target Jetson |
| `silero_vad.onnx` | Local voice activity detector | `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3` | Download and verify |

TensorRT engines are coupled to the TensorRT/CUDA/GPU stack. Do not copy an
engine from a different JetPack release and call it recovered. Run:

```bash
./scripts/restore_models.sh
python scripts/export_tensorrt.py --model models/atlas_yolo.pt --imgsz 416
```

The old nationals repository is preserved under
`../legacy/nationals_2026/`, including the original training dataset, runs,
`best.pt`, `last.pt`, and base `yolo26n.pt` checkpoint.
