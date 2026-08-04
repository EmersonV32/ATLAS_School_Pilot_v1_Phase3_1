#!/usr/bin/env bash
set -euo pipefail
source ~/atlas/venvs/yolo-runtime/bin/activate
python -m pip install --force-reinstall 'numpy==1.26.4'
python - <<'PY'
import torch, torchvision, numpy
print('torch', torch.__version__)
print('torchvision', torchvision.__version__)
print('cuda', torch.cuda.is_available())
print('numpy', numpy.__version__)
print('gpu', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')
PY