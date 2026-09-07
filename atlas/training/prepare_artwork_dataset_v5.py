"""Build leakage-resistant ATLAS v5 splits from the Roboflow v4 export."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT / "datasets" / "futureinnovators-v4"
DEFAULT_DESTINATION = ROOT / "datasets" / "atlas-artworks-v5-base"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
CLASS_NAMES = [
    "girl_with_a_pearl_earring",
    "great_wave_off_kanagawa",
    "liberty_leading_the_people",
    "mona_lisa",
    "tutankhamun_mask",
    "starry_night",
    "sunflowers",
]
SOURCE_CLASS_NAMES = [
    "earring",
    "kanagawa",
    "liberty",
    "mona_lisa",
    "pharaoh_mask",
    "starry_night",
    "sunflowers",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_DESTINATION)
    return parser.parse_args()


def source_key(path: Path) -> str:
    return path.stem.split(".rf.", 1)[0]


def capture_number(key: str) -> tuple[str, int] | None:
    clean = re.sub(r"_(?:jpe?g|png)$", "", key, flags=re.I)
    image_match = re.match(r"^IMG_(\d+)", clean, flags=re.I)
    if image_match:
        return "IMG", int(image_match.group(1))
    photo_match = re.match(r"^photo-(\d+)", clean, flags=re.I)
    if photo_match:
        return "photo", int(photo_match.group(1))
    return None


def assigned_split(key: str) -> str | None:
    """Assign whole capture ranges; None is a deliberate sequence buffer."""
    capture = capture_number(key)
    if capture is None:
        raise ValueError(f"Unrecognized capture filename: {key}")
    family, number = capture
    if family == "photo":
        if number <= 1_779_645_345_956:
            return "train"
        if number >= 1_788_376_308_983:
            return "test"
        raise ValueError(f"Unexpected photo timestamp: {key}")

    if 4_291 <= number <= 4_432:
        return "valid"
    if 4_459 <= number <= 4_525:
        return "test"
    if 4_610 <= number <= 5_054:
        return "train"
    if 5_125 <= number <= 5_163:
        return "test"
    if 5_969 <= number <= 6_681:
        return "train"
    if 6_712 <= number <= 6_849:
        return "valid"
    if 6_850 <= number <= 6_879:
        return None
    if 6_880 <= number <= 6_984:
        return "test"
    if number == 8_844:
        return "test"
    raise ValueError(f"Capture is outside the reviewed v4 ranges: {key}")


def read_classes(label: Path) -> set[int]:
    if not label.is_file():
        return set()
    classes: set[int] = set()
    for line in label.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if fields:
            class_id = int(fields[0])
            if class_id < 0 or class_id >= len(CLASS_NAMES):
                raise ValueError(f"Invalid class {class_id} in {label}")
            classes.add(class_id)
    return classes


def verify_source_contract(source: Path) -> None:
    metadata = yaml.safe_load((source / "data.yaml").read_text(encoding="utf-8"))
    if list(metadata.get("names", [])) != SOURCE_CLASS_NAMES:
        raise ValueError(
            "Unexpected Roboflow class order: " f"{metadata.get('names')!r}"
        )


def collect_images(source: Path) -> list[tuple[Path, Path]]:
    records: list[tuple[Path, Path]] = []
    seen: set[str] = set()
    for original_split in ("train", "valid", "test"):
        image_dir = source / original_split / "images"
        label_dir = source / original_split / "labels"
        for image in sorted(image_dir.iterdir()):
            if image.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            key = source_key(image)
            if key in seen:
                raise ValueError(f"Duplicate Roboflow source image: {key}")
            seen.add(key)
            records.append((image, label_dir / f"{image.stem}.txt"))
    return records


def write_dataset(source: Path, output: Path) -> dict[str, object]:
    if output.resolve() == source.resolve():
        raise ValueError("Output must differ from the source dataset")
    verify_source_contract(source)
    records = collect_images(source)
    if output.exists():
        shutil.rmtree(output)
    for split in ("train", "valid", "test"):
        (output / split / "images").mkdir(parents=True)
        (output / split / "labels").mkdir(parents=True)

    image_counts: Counter[str] = Counter()
    box_counts = {split: Counter() for split in ("train", "valid", "test")}
    excluded: list[str] = []
    manifest: dict[str, str] = {}
    for image, label in records:
        key = source_key(image)
        split = assigned_split(key)
        if split is None:
            excluded.append(key)
            continue
        shutil.copy2(image, output / split / "images" / image.name)
        if label.is_file():
            shutil.copy2(label, output / split / "labels" / label.name)
        image_counts[split] += 1
        manifest[key] = split
        for class_id in read_classes(label):
            box_counts[split][class_id] += 1

    for split in ("train", "valid", "test"):
        missing = [
            CLASS_NAMES[class_id]
            for class_id in range(len(CLASS_NAMES))
            if box_counts[split][class_id] == 0
        ]
        if missing:
            raise ValueError(f"{split} split is missing classes: {missing}")

    data_yaml = {
        "path": output.resolve().as_posix(),
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "names": CLASS_NAMES,
        "nc": len(CLASS_NAMES),
    }
    (output / "data.yaml").write_text(
        yaml.safe_dump(data_yaml, sort_keys=False), encoding="utf-8"
    )
    report: dict[str, object] = {
        "source": str(source.resolve()),
        "output": str(output.resolve()),
        "policy": "reviewed_capture_ranges_v1",
        "images": dict(image_counts),
        "class_boxes": {
            split: {
                CLASS_NAMES[class_id]: box_counts[split][class_id]
                for class_id in range(len(CLASS_NAMES))
            }
            for split in ("train", "valid", "test")
        },
        "excluded_sequence_buffer": sorted(excluded),
        "assignments": dict(sorted(manifest.items())),
    }
    (output / "split_manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    args = parse_args()
    report = write_dataset(args.source, args.output)
    print(json.dumps({key: report[key] for key in ("images", "class_boxes")}, indent=2))
    print(f"Prepared leakage-resistant dataset: {args.output}")


if __name__ == "__main__":
    main()
