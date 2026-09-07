#!/usr/bin/env python3
"""Audit YOLO dataset splits for duplicate and neighboring capture leakage."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True)
class ImageRecord:
    path: Path
    classes: frozenset[int]
    sha256: str
    source_key: str
    sequence_prefix: str | None
    sequence_number: int | None
    perceptual_hash: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="Dataset root containing train, valid, and test directories",
    )
    return parser.parse_args()


def source_identity(path: Path) -> tuple[str, str | None, int | None]:
    source_key = path.stem.split(".rf.", 1)[0]
    match = re.match(r"^(.*?)(\d+)(?:_(?:jpe?g|png))?$", source_key, re.I)
    if not match:
        return source_key, None, None
    return source_key, match.group(1).lower(), int(match.group(2))


def read_classes(label_path: Path) -> frozenset[int]:
    if not label_path.is_file():
        return frozenset()
    classes: set[int] = set()
    for line in label_path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if fields:
            classes.add(int(fields[0]))
    return frozenset(classes)


def image_phash(path: Path) -> int:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Cannot decode image: {path}")
    resized = cv2.resize(image, (32, 32), interpolation=cv2.INTER_AREA)
    coefficients = cv2.dct(resized.astype(np.float32))[:8, :8].flatten()
    median = float(np.median(coefficients[1:]))
    value = 0
    for bit in coefficients > median:
        value = (value << 1) | int(bit)
    return value


def load_split(dataset: Path, split: str) -> list[ImageRecord]:
    image_dir = dataset / split / "images"
    label_dir = dataset / split / "labels"
    records: list[ImageRecord] = []
    for path in sorted(image_dir.iterdir()):
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        source_key, sequence_prefix, sequence_number = source_identity(path)
        records.append(
            ImageRecord(
                path=path,
                classes=read_classes(label_dir / f"{path.stem}.txt"),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                source_key=source_key,
                sequence_prefix=sequence_prefix,
                sequence_number=sequence_number,
                perceptual_hash=image_phash(path),
            )
        )
    return records


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def compare_split(
    reference: list[ImageRecord], candidate: list[ImageRecord]
) -> dict[str, object]:
    reference_hashes = {record.sha256 for record in reference}
    reference_sources = {record.source_key for record in reference}
    exact_hash = 0
    exact_source = 0
    adjacent = {1: 0, 2: 0, 5: 0}
    adjacent_examples: list[dict[str, object]] = []
    nearest_phash: list[int] = []

    for current in candidate:
        exact_hash += current.sha256 in reference_hashes
        exact_source += current.source_key in reference_sources
        comparable = [
            item
            for item in reference
            if not current.classes
            or not item.classes
            or bool(current.classes & item.classes)
        ]
        if comparable:
            nearest_phash.append(
                min(
                    hamming_distance(current.perceptual_hash, item.perceptual_hash)
                    for item in comparable
                )
            )
        if current.sequence_prefix is None or current.sequence_number is None:
            continue
        sequence_candidates = [
            (
                abs(current.sequence_number - item.sequence_number),
                item,
            )
            for item in comparable
            if item.sequence_prefix == current.sequence_prefix
            and item.sequence_number is not None
        ]
        if not sequence_candidates:
            continue
        minimum, nearest = min(sequence_candidates, key=lambda value: value[0])
        for window in adjacent:
            adjacent[window] += minimum <= window
        if minimum <= 1 and len(adjacent_examples) < 12:
            adjacent_examples.append(
                {
                    "candidate": current.path.name,
                    "reference": nearest.path.name,
                    "sequence_delta": minimum,
                    "phash_distance": hamming_distance(
                        current.perceptual_hash, nearest.perceptual_hash
                    ),
                    "classes": sorted(current.classes),
                }
            )

    denominator = max(1, len(candidate))
    sorted_distances = sorted(nearest_phash)
    return {
        "images": len(candidate),
        "exact_file_hash_overlap": exact_hash,
        "same_source_key_overlap": exact_source,
        "sequence_neighbor_overlap": {
            f"within_{window}": {
                "count": count,
                "percent": round(100.0 * count / denominator, 2),
            }
            for window, count in adjacent.items()
        },
        "sequence_neighbor_examples": adjacent_examples,
        "nearest_same_class_phash_distance": {
            "minimum": min(sorted_distances) if sorted_distances else None,
            "median": (
                sorted_distances[len(sorted_distances) // 2]
                if sorted_distances
                else None
            ),
            "maximum": max(sorted_distances) if sorted_distances else None,
            "within_4_bits": sum(value <= 4 for value in sorted_distances),
        },
    }


def main() -> int:
    args = parse_args()
    train = load_split(args.dataset, "train")
    report = {
        "dataset": str(args.dataset),
        "train_images": len(train),
        "valid_vs_train": compare_split(train, load_split(args.dataset, "valid")),
        "test_vs_train": compare_split(train, load_split(args.dataset, "test")),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
