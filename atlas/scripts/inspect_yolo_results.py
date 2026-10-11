#!/usr/bin/env python3
"""Inspect a mentor results ZIP without extracting it or executing a checkpoint.

This is metadata verification, NOT inference, pickle safety certification, or
authorization to promote a detector. Run the existing real-loader verifier and
camera/TensorRT release gates on the approved test device before deployment.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import pickletools
import zipfile
from pathlib import Path

from atlas.vision.artwork_release import load_model_labels


def embedded_names(checkpoint: bytes) -> list[str]:
    """Read the literal numeric names dictionary in this checkpoint format.

    Never use pickle.load/torch.load here. Unsupported layouts fail closed and
    need a real-loader check in an isolated environment.
    """
    with zipfile.ZipFile(io.BytesIO(checkpoint)) as archive:
        entries = [e for e in archive.infolist() if e.filename.endswith("/data.pkl")]
        if len(entries) != 1 or entries[0].file_size > 8 * 1024 * 1024:
            raise ValueError("Missing, ambiguous or oversized checkpoint metadata")
        ops = list(pickletools.genops(archive.read(entries[0])))
    starts = [
        i
        for i, (op, arg, _) in enumerate(ops)
        if op.name in {"BINUNICODE", "SHORT_BINUNICODE"} and arg == "names"
    ]
    if len(starts) != 1:
        raise ValueError("Unsupported embedded class-name layout")
    ignored = {"BINPUT", "LONG_BINPUT", "MEMOIZE"}
    values = []
    for op, arg, _ in ops[starts[0] + 1 :]:
        if op.name in ignored:
            continue
        if op.name == "SETITEMS":
            break
        values.append((op.name, arg))
        if len(values) > 200:
            raise ValueError("Oversized embedded class dictionary")
    else:
        raise ValueError("Unterminated embedded class dictionary")
    if values[:2] != [("EMPTY_DICT", None), ("MARK", None)]:
        raise ValueError("Expected a literal embedded class dictionary")
    pairs = values[2:]
    if not pairs or len(pairs) % 2:
        raise ValueError("Malformed class dictionary")
    names = []
    for i in range(0, len(pairs), 2):
        index_op, index = pairs[i]
        name_op, name = pairs[i + 1]
        if index_op not in {"BININT", "BININT1", "BININT2", "INT"} or index != i // 2:
            raise ValueError("Class indices are not contiguous and ordered")
        if name_op not in {"BINUNICODE", "SHORT_BINUNICODE"} or not isinstance(
            name, str
        ):
            raise ValueError("Class names must be literal strings")
        names.append(name)
    return names


def inspect_results(results_zip: Path, candidate: Path, labels: Path) -> dict:
    with zipfile.ZipFile(results_zip) as archive:

        def unique(suffix: str, limit: int):
            entries = [e for e in archive.infolist() if e.filename.endswith(suffix)]
            if len(entries) != 1 or entries[0].file_size > limit:
                raise ValueError(f"Missing, ambiguous or oversized {suffix}")
            return archive.read(entries[0])

        checkpoint = unique("/best.pt", 64 * 1024 * 1024)
        evaluation = json.loads(unique("/atlas_evaluation.json", 1024 * 1024))
    digest = hashlib.sha256(checkpoint).hexdigest()
    if digest != evaluation["checkpoint_sha256"]:
        raise ValueError("Checkpoint does not match its evaluation report")
    if digest != hashlib.sha256(candidate.read_bytes()).hexdigest():
        raise ValueError("Selected candidate differs from the supplied results")
    expected, actual = load_model_labels(labels), embedded_names(checkpoint)
    if actual != expected or evaluation["dataset"]["classes"] != expected:
        raise ValueError("Checkpoint/report class order differs from ATLAS labels")
    for size in (640, 416):
        report = evaluation[f"test_{size}"]
        if set(report["per_class"]) != set(expected):
            raise ValueError("Incomplete per-class evaluation")
        for metric, per_class_metric in (("map50", "ap50"), ("map50_95", "ap50_95")):
            values = [report["per_class"][name][per_class_metric] for name in expected]
            if not all(math.isfinite(v) and 0 <= v <= 1 for v in values):
                raise ValueError("Invalid AP values")
            if not math.isclose(
                sum(values) / len(values), report[metric], abs_tol=1e-6
            ):
                raise ValueError("Reported mAP disagrees with per-class AP")
    return {
        "metadata_verified": True,
        "checkpoint_sha256": digest,
        "embedded_classes": actual,
        "candidate_matches_supplied_zip": True,
        "test_416_map50": evaluation["test_416"]["map50"],
        "test_416_map50_95": evaluation["test_416"]["map50_95"],
        "inference_verified": False,
        "deployment_ready": False,
        "pending": [
            "fresh XIAO-camera holdout and false-alarm review",
            "Jetson real-loader compatibility and PT/TensorRT parity at 416",
            "end-to-end timing and sustained thermals",
            "explicit hardware deployment approval",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-zip", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--labels", type=Path, default=Path("config/artwork_labels.yaml")
    )
    args = parser.parse_args()
    try:
        result = inspect_results(args.results_zip, args.candidate, args.labels)
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"Results verification failed: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
