"""Command-line gate for a new Roboflow/YOLO artwork release."""

from __future__ import annotations

import argparse
import json

from atlas.vision.artwork_release import validate_artwork_release


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate YOLO labels against an ATLAS content pack"
    )
    parser.add_argument("--pack", required=True, help="Content-pack directory")
    parser.add_argument(
        "--labels", required=True, help="Roboflow data.yaml, labels JSON, or TXT"
    )
    parser.add_argument(
        "--require-all-content-detectable",
        action="store_true",
        help="Fail if a content entry is absent from the detector label list",
    )
    args = parser.parse_args()
    report = validate_artwork_release(
        args.pack,
        args.labels,
        require_all_content_detectable=args.require_all_content_detectable,
    )
    print(json.dumps(report.as_dict(), indent=2))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
