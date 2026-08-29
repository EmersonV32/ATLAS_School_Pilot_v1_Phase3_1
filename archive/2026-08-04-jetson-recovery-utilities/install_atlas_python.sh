#!/usr/bin/env bash
set -euo pipefail
source ~/atlas/venvs/yolo-runtime/bin/activate
python -m pip install --upgrade \
  sounddevice python-dotenv google-genai langdetect tenacity beautifulsoup4 requests PyYAML pillow tqdm psutil
python -m pip install --upgrade faster-whisper
python -m pip install --upgrade chromadb sentence-transformers
python -m pip install --upgrade ultralytics
python -m pip install --upgrade piper-tts
python -m pip check