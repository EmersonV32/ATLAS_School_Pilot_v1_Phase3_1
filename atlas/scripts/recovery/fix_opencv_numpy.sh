#!/usr/bin/env bash
set -euo pipefail
source ~/atlas/venvs/yolo-runtime/bin/activate
python -m pip uninstall -y opencv-python
python -m pip install --force-reinstall 'numpy==1.26.4' 'opencv-python==4.10.0.84'
python -m pip check
python - <<'PY'
import numpy, cv2, torch
print('numpy', numpy.__version__)
print('cv2', cv2.__version__)
print('torch', torch.__version__, 'cuda', torch.cuda.is_available())
PY