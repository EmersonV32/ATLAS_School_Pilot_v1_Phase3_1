#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ATLAS_VENV_PATH="${ATLAS_VENV_PATH:-$HOME/atlas/venvs/atlas-school-pilot}"

# Refuse a competing manual pipeline before activating or loading its models.
# Missing systemd/a user bus is normal on some manual-launch environments.
if command -v systemctl >/dev/null 2>&1 &&
  systemctl --user is-active --quiet atlas.service 2>/dev/null; then
  printf '%s\n' 'ATLAS is already running through atlas.service. Use its dashboard or stop the service before a manual launch.' >&2
  exit 1
fi

cd "$PROJECT_DIR"
source "$ATLAS_VENV_PATH/bin/activate"
export ATLAS_MODE=device
exec python -m atlas.app.main --mode device --device-loop --wait-ready "$@"
