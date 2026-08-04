#!/usr/bin/env bash
set -euo pipefail
source ~/atlas/venvs/yolo-runtime/bin/activate
cd ~/atlas/wrofutureinnovators2026
python - <<'PY'
import time
import numpy as np
from faster_whisper import WhisperModel
from ultralytics import YOLO
from atlas.rag import RAG

print('prewarm whisper tiny cpu int8')
t0 = time.time()
whisper = WhisperModel('tiny', device='cpu', compute_type='int8')
print('whisper ready', round(time.time() - t0, 2), 's')

print('prewarm rag')
t0 = time.time()
rag = RAG()
print('rag ready', round(time.time() - t0, 2), 'sheets', len(rag.sheets))

print('prewarm yolo cuda')
t0 = time.time()
model = YOLO('best.pt')
model.to('cuda')
dummy = np.zeros((416, 416, 3), dtype=np.uint8)
res = model.predict(dummy, imgsz=416, verbose=False, device=0)
print('yolo ready', round(time.time() - t0, 2), 'detections', len(res))
PY