"""Prepare a Roboflow YOLO export for the ATLAS artwork-label contract."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "datasets" / "futureinnovators-v4"
DESTINATION = ROOT / "datasets" / "atlas-artworks-v4"

LABEL_MAP = {
    "earring": "girl_with_a_pearl_earring",
    "kanagawa": "great_wave_off_kanagawa",
    "liberty": "liberty_leading_the_people",
    "mona_lisa": "mona_lisa",
    "pharaoh_mask": "tutankhamun_mask",
    "starry_night": "starry_night",
    "sunflowers": "sunflowers",
}


def main() -> None:
    source_config = SOURCE / "data.yaml"
    if not source_config.is_file():
        raise FileNotFoundError(
            f"Expected the Roboflow export at {source_config}. Extract the ZIP first."
        )

    source_text = source_config.read_text(encoding="utf-8")
    names_line = next(
        (line for line in source_text.splitlines() if line.startswith("names:")),
        None,
    )
    if names_line is None:
        raise ValueError("Roboflow data.yaml does not contain an inline names list")
    source_names = [
        name.strip().strip("'\"")
        for name in names_line.partition("[")[2].removesuffix("]").split(",")
        if name.strip()
    ]
    unknown = sorted(set(source_names) - set(LABEL_MAP))
    missing = sorted(set(LABEL_MAP) - set(source_names))
    if unknown or missing:
        raise ValueError(f"Unexpected class contract. Unknown={unknown}; missing={missing}")

    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    shutil.copytree(SOURCE, DESTINATION)

    target_names = [LABEL_MAP[name] for name in source_names]
    prepared_config = "\n".join(
        [
            f"path: {DESTINATION.resolve().as_posix()}",
            "train: train/images",
            "val: valid/images",
            "test: test/images",
            "names:",
            *[f"  - {name}" for name in target_names],
            "",
        ]
    )
    (DESTINATION / "data.yaml").write_text(prepared_config, encoding="utf-8")
    print(f"Prepared dataset: {DESTINATION}")
    print(f"Classes: {target_names}")


if __name__ == "__main__":
    main()
