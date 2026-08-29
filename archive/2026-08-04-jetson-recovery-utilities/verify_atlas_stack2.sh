#!/usr/bin/env bash
set -euo pipefail
source ~/atlas/venvs/yolo-runtime/bin/activate
cd ~/atlas/wrofutureinnovators2026
python - <<'PY'
mods = [
    ('numpy', 'numpy'),
    ('cv2', 'cv2'),
    ('torch', 'torch'),
    ('torchvision', 'torchvision'),
    ('ultralytics', 'ultralytics'),
    ('sounddevice', 'sounddevice'),
    ('dotenv', 'dotenv'),
    ('google.genai', 'google.genai'),
    ('faster_whisper', 'faster_whisper'),
    ('chromadb', 'chromadb'),
    ('sentence_transformers', 'sentence_transformers'),
    ('langdetect', 'langdetect'),
]
for name, mod in mods:
    m = __import__(mod, fromlist=['*'])
    print(name, getattr(m, '__version__', 'ok'))
import torch
print('torch_cuda', torch.cuda.is_available())
print('torch_gpu', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')
from ultralytics import YOLO
model = YOLO('best.pt')
print('yolo_loaded', model.names)
from atlas.rag import RAG
rag = RAG()
print('rag_sheets', len(rag.sheets), list(rag.sheets.keys()))
PY
python -m piper --help >/tmp/piper_help.txt 2>&1 && echo 'piper module ok' || (cat /tmp/piper_help.txt; exit 1)