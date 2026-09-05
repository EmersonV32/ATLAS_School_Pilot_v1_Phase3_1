#!/usr/bin/env python3
"""Verify that the portable YOLO checkpoint embeds the ATLAS class order."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from atlas.vision.artwork_release import load_model_labels


def _ordered_names(names: Any) -> list[str]:
    if isinstance(names, dict):
        return [str(names[key]) for key in sorted(names, key=int)]
    if isinstance(names, (list, tuple)):
        return [str(name) for name in names]
    raise TypeError(f"Unsupported model names payload: {type(names).__name__}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="models/atlas_yolo.pt")
    parser.add_argument("--labels", default="config/artwork_labels.yaml")
    args = parser.parse_args()

    jetpack_packages = Path("/usr/lib/python3.10/dist-packages")
    if jetpack_packages.is_dir():
        sys.path.append(str(jetpack_packages))

    from ultralytics import YOLO  # type: ignore

    model_path = Path(args.model)
    if not model_path.is_file():
        raise SystemExit(f"Model not found: {model_path}")

    expected = load_model_labels(args.labels)
    actual = _ordered_names(YOLO(str(model_path), task="detect").names)
    valid = actual == expected
    result = {"valid": valid, "expected": expected, "actual": actual}
    print(json.dumps(result, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
