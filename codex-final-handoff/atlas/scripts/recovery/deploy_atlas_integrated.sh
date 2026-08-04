#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ARCHIVE="/tmp/atlas-integrated.tar.gz"
DEPLOY_TARGET="$HOME/atlas/ATLAS_School_Pilot_v1_integrated"
DEPLOY_VENV="$HOME/atlas/venvs/atlas-school-pilot"
HEAVY_SITE="$HOME/atlas/venvs/yolo-runtime/lib/python3.10/site-packages"

if [ -e "$DEPLOY_TARGET" ]; then
    echo "Refusing to overwrite existing target: $DEPLOY_TARGET" >&2
    exit 2
fi
if [ -e "$DEPLOY_VENV" ]; then
    echo "Refusing to overwrite existing venv: $DEPLOY_VENV" >&2
    exit 2
fi

mkdir -p "$DEPLOY_TARGET" "$(dirname "$DEPLOY_VENV")"
tar -xzf "$DEPLOY_ARCHIVE" -C "$DEPLOY_TARGET"
python3 -m venv "$DEPLOY_VENV"

SITE_DIR="$($DEPLOY_VENV/bin/python -c 'import site; print(site.getsitepackages()[0])')"
printf '%s\n' "$HEAVY_SITE" > "$SITE_DIR/atlas-heavy-runtime.pth"

source "$DEPLOY_VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install -e "$DEPLOY_TARGET[dev,rag,llm]"

mkdir -p "$DEPLOY_TARGET/models"
cp "$HOME/atlas/wrofutureinnovators2026/best.pt" \
   "$DEPLOY_TARGET/models/atlas_yolo.pt"
chmod +x "$DEPLOY_TARGET/scripts/start_device.sh"
chmod +x "$DEPLOY_TARGET/scripts/preflight_device.sh"

cd "$DEPLOY_TARGET"
python -m pip check
python -m pytest -q
python -m atlas.app.preflight || true

echo "Deployment ready: $DEPLOY_TARGET"
echo "Environment ready: $DEPLOY_VENV"
