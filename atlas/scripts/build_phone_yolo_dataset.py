"""Add synthetic phone-display scenes to an existing YOLO detection dataset."""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

import cv2
import numpy as np
import yaml

CLASS_IDS = {
    "girl_with_a_pearl_earring": 0,
    "great_wave_off_kanagawa": 1,
    "liberty_leading_the_people": 2,
    "mona_lisa": 3,
    "tutankhamun_mask": 4,
    "starry_night": 5,
    "sunflowers": 6,
}
NEW_ARTWORKS = {key: value for key, value in CLASS_IDS.items() if value in {0, 1, 2, 6}}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--background", type=Path)
    parser.add_argument("--samples-per-class", type=int, default=180)
    parser.add_argument("--seed", type=int, default=260907)
    return parser.parse_args()


def copy_dataset(source: Path, output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    for split in ("train", "valid", "test"):
        shutil.copytree(source / split, output / split)
    metadata = yaml.safe_load((source / "data.yaml").read_text(encoding="utf-8"))
    metadata["train"] = "train/images"
    metadata["val"] = "valid/images"
    metadata["test"] = "test/images"
    metadata["names"] = list(CLASS_IDS)
    metadata["nc"] = len(CLASS_IDS)
    (output / "data.yaml").write_text(
        yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8"
    )


def make_background(rng: random.Random, source: np.ndarray | None) -> np.ndarray:
    height, width = 600, 800
    if source is not None:
        canvas = cv2.resize(source, (width, height))
        canvas = cv2.GaussianBlur(canvas, (0, 0), rng.uniform(24, 45))
        canvas = cv2.convertScaleAbs(
            canvas, alpha=rng.uniform(0.65, 1.05), beta=rng.randint(-25, 25)
        )
    else:
        base = np.array(
            [rng.randint(30, 190), rng.randint(30, 190), rng.randint(30, 190)],
            dtype=np.float32,
        )
        noise = np.random.default_rng(rng.randrange(2**32)).normal(
            0, rng.uniform(5, 18), (height, width, 3)
        )
        canvas = np.clip(base + noise, 0, 255).astype(np.uint8)
        canvas = cv2.GaussianBlur(canvas, (0, 0), rng.uniform(3, 12))
    return canvas


def fit_artwork(reference: np.ndarray, width: int, height: int) -> np.ndarray:
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    scale = min(width / reference.shape[1], height / reference.shape[0])
    resized = cv2.resize(
        reference,
        (
            max(1, round(reference.shape[1] * scale)),
            max(1, round(reference.shape[0] * scale)),
        ),
        interpolation=cv2.INTER_AREA,
    )
    x = (width - resized.shape[1]) // 2
    y = (height - resized.shape[0]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    return canvas


def synthesize(
    reference: np.ndarray,
    background: np.ndarray,
    rng: random.Random,
) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    frame_h, frame_w = background.shape[:2]
    portrait = reference.shape[0] >= reference.shape[1]
    if portrait:
        screen_h = rng.randint(310, 500)
        screen_w = rng.randint(210, min(390, int(screen_h * 0.9)))
    else:
        screen_w = rng.randint(330, 620)
        screen_h = rng.randint(210, min(410, int(screen_w * 0.85)))
    center_x = rng.randint(screen_w // 2 + 25, frame_w - screen_w // 2 - 25)
    center_y = rng.randint(screen_h // 2 + 25, frame_h - screen_h // 2 - 25)
    x1, y1 = center_x - screen_w // 2, center_y - screen_h // 2
    x2, y2 = x1 + screen_w, y1 + screen_h
    jitter = max(5, round(min(screen_w, screen_h) * 0.08))
    quad = np.float32(
        [
            [x1 + rng.randint(-jitter, jitter), y1 + rng.randint(-jitter, jitter)],
            [x2 + rng.randint(-jitter, jitter), y1 + rng.randint(-jitter, jitter)],
            [x2 + rng.randint(-jitter, jitter), y2 + rng.randint(-jitter, jitter)],
            [x1 + rng.randint(-jitter, jitter), y2 + rng.randint(-jitter, jitter)],
        ]
    )
    bezel = max(8, round(min(screen_w, screen_h) * rng.uniform(0.035, 0.075)))
    outer = quad.copy()
    outer[[0, 3], 0] -= bezel
    outer[[1, 2], 0] += bezel
    outer[[0, 1], 1] -= bezel
    outer[[2, 3], 1] += bezel
    cv2.fillConvexPoly(background, outer.astype(np.int32), (8, 10, 12))

    artwork = fit_artwork(reference, screen_w, screen_h)
    artwork = cv2.convertScaleAbs(
        artwork, alpha=rng.uniform(0.65, 1.35), beta=rng.randint(-20, 55)
    )
    source_quad = np.float32(
        [[0, 0], [screen_w - 1, 0], [screen_w - 1, screen_h - 1], [0, screen_h - 1]]
    )
    matrix = cv2.getPerspectiveTransform(source_quad, quad)
    warped = cv2.warpPerspective(artwork, matrix, (frame_w, frame_h))
    mask = cv2.warpPerspective(
        np.full((screen_h, screen_w), 255, dtype=np.uint8),
        matrix,
        (frame_w, frame_h),
    )
    background[mask > 0] = warped[mask > 0]

    if rng.random() < 0.7:
        overlay = background.copy()
        glare_x = rng.randint(int(quad[:, 0].min()), int(quad[:, 0].max()))
        cv2.line(
            overlay,
            (glare_x, max(0, int(quad[:, 1].min()))),
            (
                min(frame_w - 1, glare_x + rng.randint(35, 130)),
                min(frame_h - 1, int(quad[:, 1].max())),
            ),
            (255, 255, 255),
            rng.randint(18, 60),
        )
        glare_alpha = rng.uniform(0.08, 0.25)
        cv2.addWeighted(
            overlay, glare_alpha, background, 1.0 - glare_alpha, 0, background
        )
    if rng.random() < 0.85:
        background = cv2.GaussianBlur(background, (0, 0), rng.uniform(0.4, 2.2))
    if rng.random() < 0.55:
        small_w = rng.randint(320, 560)
        small_h = round(frame_h * small_w / frame_w)
        background = cv2.resize(
            cv2.resize(background, (small_w, small_h)), (frame_w, frame_h)
        )

    bx1 = max(0.0, float(quad[:, 0].min()) / frame_w)
    by1 = max(0.0, float(quad[:, 1].min()) / frame_h)
    bx2 = min(1.0, float(quad[:, 0].max()) / frame_w)
    by2 = min(1.0, float(quad[:, 1].max()) / frame_h)
    return background, (bx1, by1, bx2, by2)


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    copy_dataset(args.source, args.output)
    background = cv2.imread(str(args.background)) if args.background else None
    image_dir = args.output / "train/images"
    label_dir = args.output / "train/labels"
    for artwork_id, class_id in NEW_ARTWORKS.items():
        reference = cv2.imread(str(args.references / f"{artwork_id}.jpg"))
        if reference is None:
            raise FileNotFoundError(f"Missing reference for {artwork_id}")
        for index in range(args.samples_per_class):
            frame, (x1, y1, x2, y2) = synthesize(
                reference, make_background(rng, background), rng
            )
            stem = f"phone_{artwork_id}_{index:04d}"
            cv2.imwrite(
                str(image_dir / f"{stem}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 82]
            )
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            width, height = x2 - x1, y2 - y1
            (label_dir / f"{stem}.txt").write_text(
                f"{class_id} {cx:.6f} {cy:.6f} {width:.6f} {height:.6f}\n",
                encoding="ascii",
            )
    sample_count = args.samples_per_class * len(NEW_ARTWORKS)
    print(f"Built {args.output} with {sample_count} phone scenes")


if __name__ == "__main__":
    main()
