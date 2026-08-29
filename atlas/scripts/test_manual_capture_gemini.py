"""Exercise manual artwork identification on supplied images using Gemini."""

from __future__ import annotations

import argparse

import cv2  # type: ignore

from atlas.app.dependency_container import build_container
from atlas.models.enums import RunMode


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+")
    parser.add_argument("--config-dir", default="config")
    args = parser.parse_args()

    container = build_container(args.config_dir)
    container.settings.mode = RunMode.DEVICE
    capture = container.manual_artwork_capture
    if capture is None:
        raise SystemExit("Manual capture is disabled or Gemini is not configured")

    for path in args.images:
        frame = cv2.imread(path)
        if frame is None:
            print(f"{path}: unreadable")
            continue
        detection = capture.identify(frame)
        answer = detection.artwork_id if detection else "unknown"
        print(f"{path}: {answer}")


if __name__ == "__main__":
    main()
