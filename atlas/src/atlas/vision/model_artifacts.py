"""Bind a generated TensorRT engine to its portable checkpoint and input size."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def engine_manifest_path(engine: str | Path) -> Path:
    return Path(str(engine) + ".manifest.json")


def write_engine_manifest(
    checkpoint: str | Path, engine: str | Path, image_size: int
) -> Path:
    """Call only after a successful, on-target export; never ship this sidecar."""
    payload = {
        "schema_version": 1,
        "checkpoint_sha256": sha256_file(checkpoint),
        "engine_sha256": sha256_file(engine),
        "image_size": image_size,
    }
    manifest = engine_manifest_path(engine)
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest


def engine_matches_checkpoint(
    checkpoint: str | Path, engine: str | Path, image_size: int
) -> bool:
    """Missing, legacy, corrupt or stale artifacts must never win auto selection."""
    try:
        payload = json.loads(engine_manifest_path(engine).read_text(encoding="utf-8"))
        return (
            isinstance(payload, dict)
            and payload.get("schema_version") == 1
            and payload.get("image_size") == image_size
            and payload.get("checkpoint_sha256") == sha256_file(checkpoint)
            and payload.get("engine_sha256") == sha256_file(engine)
        )
    except (OSError, ValueError, TypeError):
        return False


def select_yolo_model(
    checkpoint: str, engine: str, backend: str, image_size: int
) -> tuple[str, str | None]:
    if backend != "pytorch" and engine_matches_checkpoint(
        checkpoint, engine, image_size
    ):
        return engine, checkpoint
    if backend == "tensorrt" or (backend == "auto" and Path(engine).is_file()):
        logger.warning(
            "TensorRT engine lacks matching checkpoint/input-size provenance; "
            "using the portable PyTorch model. Re-export on the target Jetson."
        )
    return checkpoint, None
