#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="${ATLAS_VENV_PATH:-$HOME/atlas/venvs/atlas-school-pilot}"

if [[ "$(uname -m)" != "aarch64" ]]; then
    printf 'ERROR: this bootstrap is for the Jetson aarch64 host.\n' >&2
    exit 2
fi
if [[ ! -f /etc/nv_tegra_release ]]; then
    printf 'ERROR: NVIDIA L4T release metadata is missing.\n' >&2
    exit 2
fi

printf 'This script does not run apt upgrade and does not change nvidia-l4t packages.\n'
sudo apt-get update
sudo apt-get install -y \
    git git-lfs python3-pip python3-venv python3-dev \
    build-essential cmake curl wget unzip ffmpeg portaudio19-dev \
    v4l-utils bluetooth bluez alsa-utils

python3 -m venv --system-site-packages "$VENV"
source "$VENV/bin/activate"
python -m pip install --upgrade pip setuptools wheel
cd "$PROJECT_DIR"

# JetPack 6 compatible CUDA builds. Install these before the exact lock so pip
# does not search public PyPI for an incompatible ARM wheel.
python -m pip install torch==2.8.0 torchvision==0.23.0 \
    --index-url https://pypi.jetson-ai-lab.io/jp6/cu126
python -m pip install -r "$PROJECT_DIR/requirements-jetson.lock.txt"
python -m pip install --force-reinstall \
    numpy==1.26.4 opencv-python==4.10.0.84 scipy==1.11.4
python -m pip install -e "$PROJECT_DIR"

cd "$PROJECT_DIR"
./scripts/restore_models.sh
python -m piper.download_voices --download-dir "$HOME/piper_voices" \
    en_US-ryan-low fr_FR-siwis-medium es_MX-claude-high it_IT-paola-medium

# Prime local caches while network access is available. The runtime later uses
# local-files-only mode and should not download models at boot.
python - <<'PY'
from faster_whisper import WhisperModel
from sentence_transformers import SentenceTransformer

WhisperModel("small", device="cpu", compute_type="int8")
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
print("Whisper and embedding caches are ready.")
PY

python scripts/export_tensorrt.py --model models/atlas_yolo.pt --imgsz 416
python -m atlas.rag.ingest --pack data/content_packs/demo_pack --mode device --reset
python -m pip check
python -m pytest -q
./scripts/install_user_service.sh

printf '\nBootstrap complete. Add private keys with ./scripts/configure_cloud_keys.sh\n'
printf 'Then run ./scripts/preflight_device.sh --open-camera before starting ATLAS.\n'
