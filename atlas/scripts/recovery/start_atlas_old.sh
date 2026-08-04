#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/atlas/wrofutureinnovators2026"
source "$HOME/atlas/venvs/yolo-runtime/bin/activate"
exec python JRAG2.py "$@"