#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ATLAS_VENV_PATH="${ATLAS_VENV_PATH:-$HOME/atlas/venvs/atlas-school-pilot}"

cd "$PROJECT_DIR"
source "$ATLAS_VENV_PATH/bin/activate"
export ATLAS_MODE=device
exec python -m atlas.app.main --mode device --device-loop --wait-ready "$@"
