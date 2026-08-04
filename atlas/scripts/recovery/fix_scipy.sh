#!/usr/bin/env bash
set -euo pipefail
source ~/atlas/venvs/yolo-runtime/bin/activate
python -m pip install --upgrade 'scipy==1.11.4'
python -m pip check
python - <<'PY'
import numpy, scipy
print('numpy', numpy.__version__)
print('scipy', scipy.__version__)
PY