#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MODEL_DIR="$PROJECT_DIR/models"
SILERO_URL="${ATLAS_SILERO_URL:-https://raw.githubusercontent.com/snakers4/silero-vad/master/src/silero_vad/data/silero_vad.onnx}"
YOLO_SHA="53f4438df7af6b19550cd0b508e8cde84b2e1cfdc66296564516222aca4dbc0d"
SILERO_SHA="1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"

mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

printf '%s  %s\n' "$YOLO_SHA" atlas_yolo.pt | sha256sum --check

if [[ ! -f silero_vad.onnx ]] || ! printf '%s  %s\n' "$SILERO_SHA" silero_vad.onnx | sha256sum --check --status; then
    tmp="$(mktemp "$MODEL_DIR/silero_vad.onnx.XXXXXX")"
    trap 'rm -f "$tmp"' EXIT
    curl --fail --location --retry 3 "$SILERO_URL" --output "$tmp"
    printf '%s  %s\n' "$SILERO_SHA" "$tmp" | sha256sum --check
    mv "$tmp" silero_vad.onnx
    trap - EXIT
fi

printf 'Portable ATLAS models verified.\n'
printf 'Generate the target-specific TensorRT engine with:\n'
printf '  python scripts/export_tensorrt.py --model models/atlas_yolo.pt --imgsz 416\n'
