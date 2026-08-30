#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="${ATLAS_VENV_PATH:-$HOME/atlas/venvs/atlas-school-pilot}"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_FILE="$UNIT_DIR/atlas.service"

mkdir -p "$UNIT_DIR" "$PROJECT_DIR/data/logs"
cat > "$UNIT_FILE" <<EOF
[Unit]
Description=ATLAS museum guide device runtime
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV/bin/python -m atlas.app.main --mode device --device-loop
Restart=always
RestartSec=5
TimeoutStopSec=20
KillSignal=SIGINT
StandardOutput=append:$PROJECT_DIR/data/logs/atlas-runtime.log
StandardError=append:$PROJECT_DIR/data/logs/atlas-runtime.log

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable atlas.service
printf 'Installed %s\n' "$UNIT_FILE"
printf 'Start with: systemctl --user start atlas.service\n'
