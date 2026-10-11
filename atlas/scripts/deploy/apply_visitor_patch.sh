#!/usr/bin/env bash
# Rendered by the PowerShell uploader; never run without explicit device approval.
set -euo pipefail
root='__ROOT__'
archive='__ARCHIVE__'
backup='/tmp/atlas_visitor_backup___STAMP__'
python='__PYTHON__'
staged_root='__STAGED_ROOT__'
unit="$HOME/.config/systemd/user/atlas.service"

root="$(realpath -e "$root")"
case "$root" in /|/home|/tmp|/usr|/var|/opt) echo 'Unsafe deployment root' >&2; exit 2;; esac
[[ -d "$root/src/atlas" && -f "$root/config/settings.yaml" ]]
[[ "$backup" == /tmp/atlas_visitor_backup_* && ! -e "$backup" ]]
if [[ -n "$staged_root" ]]; then
  staged_root="$(realpath -e "$staged_root")"
  [[ "$staged_root" == /tmp/atlas_v6_preflight_* && "$(dirname "$staged_root")" == /tmp ]]
fi
paths=(
  data/content_packs/demo_pack config/artwork_labels.yaml
  firmware/xiao_camera/xiao_camera.ino
  models/atlas_yolo.pt models/atlas_yolo.onnx models/atlas_yolo.engine models/manifest.sha256
  models/atlas_yolo.engine.manifest.json
  models/README.md
  models/releases/2026-09-28-yolo26n-atlas-v6/best.pt
  models/releases/2026-09-07-camera-domain-rollback
  artwork-source/mona-lisa.png artwork-source/great-wave.png
  pyproject.toml requirements.txt scripts/atlas.service scripts/check_arducam.sh
  scripts/diagnose_yolo_dataset.py scripts/diagnose_yolo_images.py
  scripts/export_tensorrt.py scripts/install_user_service.sh scripts/restore_models.sh
  scripts/inspect_yolo_results.py
  scripts/smoke_yolo_runtime.py
  scripts/run_deployment_pytest.py scripts/build_phone_yolo_dataset.py
  scripts/promote_staged_engine.py
  training/prepare_artwork_dataset_v5.py training/handoff/train.py
  scripts/validate_artwork_release.py scripts/verify_yolo_checkpoint.py
  scripts/deploy/apply_visitor_patch.sh src/atlas tests docs/PATCH_HISTORY.md
  docs/2026-10-04_FIXES_AND_V6_UPDATE.md
  docs/2026-10-04_V6_LOCAL_INTEGRATION.md
)
started=0
committed=0
was_active=0
if systemctl --user is-active --quiet atlas.service; then was_active=1; fi

restore_device_config() {
  cp -a "$backup/device_settings.yaml" "$root/config/settings.yaml" || return 1
  if [[ -f "$backup/dashboard_overrides.yaml" ]]; then
    cp -a "$backup/dashboard_overrides.yaml" "$root/config/dashboard_overrides.yaml" || return 1
  else
    rm -f "$root/config/dashboard_overrides.yaml" || return 1
  fi
}
rollback() {
  local failed=0 path
  systemctl --user stop atlas.service || failed=1
  restore_device_config || failed=1
  for path in "${paths[@]}"; do
    rm -rf "$root/$path" || failed=1
    if [[ -e "$backup/files/$path" ]]; then
      mkdir -p "$root/$(dirname "$path")" || failed=1
      cp -a "$backup/files/$path" "$root/$path" || failed=1
    fi
  done
  if [[ -f "$backup/installed_atlas.service" ]]; then
    cp -a "$backup/installed_atlas.service" "$unit" || failed=1
  else
    rm -f "$unit" || failed=1
  fi
  systemctl --user daemon-reload || failed=1
  # Never restart a partially restored tree; preserve an originally stopped service.
  if [[ "$failed" -eq 0 && "$was_active" -eq 1 ]]; then
    systemctl --user start atlas.service || failed=1
  fi
  return "$failed"
}
on_exit() {
  local status=$?
  trap - EXIT INT TERM
  if [[ "$started" -eq 1 && "$committed" -ne 1 ]]; then
    echo "Deployment failed; restoring backup: $backup" >&2
    if ! rollback; then
      echo "ROLLBACK INCOMPLETE; verify service state and recover manually from: $backup" >&2
    fi
    [[ "$status" -ne 0 ]] || status=1
  fi
  exit "$status"
}
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

mkdir -p "$backup/files"
cp -a "$root/config/settings.yaml" "$backup/device_settings.yaml"
if [[ -f "$root/config/dashboard_overrides.yaml" ]]; then
  cp -a "$root/config/dashboard_overrides.yaml" "$backup/dashboard_overrides.yaml"
fi
if [[ -f "$unit" ]]; then cp -a "$unit" "$backup/installed_atlas.service"; fi
for path in "${paths[@]}"; do
  if [[ -e "$root/$path" ]]; then
    mkdir -p "$backup/files/$(dirname "$path")"
    cp -a "$root/$path" "$backup/files/$path"
  fi
done
started=1
systemctl --user stop atlas.service
rm -rf "$root/src/atlas" "$root/tests" "$root/data/content_packs/demo_pack"
tar -xzf "$archive" -C "$root"
for path in "${paths[@]}"; do
  if [[ "$path" == *.sh && -f "$root/$path" ]]; then
    sed -i 's/\r$//' "$root/$path"
  fi
done
rm -f "$root/config/dashboard_overrides.yaml"
cd "$root"
"$python" scripts/run_deployment_pytest.py
bash scripts/restore_models.sh --verify-only
"$python" scripts/verify_yolo_checkpoint.py
rm -f "$root/models/atlas_yolo.onnx" "$root/models/atlas_yolo.engine" "$root/models/atlas_yolo.engine.manifest.json"
if [[ -n "$staged_root" ]]; then
  YOLO_AUTOINSTALL=false YOLO_OFFLINE=true "$python" scripts/promote_staged_engine.py --staged-root "$staged_root" --model models/atlas_yolo.pt --imgsz 416
else
  YOLO_AUTOINSTALL=false YOLO_OFFLINE=true "$python" scripts/export_tensorrt.py --model models/atlas_yolo.pt --imgsz 416
fi
restore_device_config
mkdir -p "$(dirname "$unit")"
install -m 0644 "$root/scripts/atlas.service" "$unit"
systemctl --user daemon-reload
systemctl --user start atlas.service
ready=0
for attempt in $(seq 1 45); do
  if curl -fsS http://127.0.0.1:8765/health > /dev/null; then ready=1; break; fi
  sleep 2
done
[[ "$ready" -eq 1 ]]
for asset in /static/visitor/assets/atlas-logo-v2.webp /static/visitor/assets/gallery-mona-lisa.webp /static/visitor/assets/gallery-great-wave.webp /static/visitor/assets/gallery-ambassadors.webp /static/visitor/assets/interest-stories.webp /static/visitor/assets/interest-technique.webp /static/visitor/assets/interest-symbols.webp /static/visitor/assets/interest-history.webp /static/visitor/assets/interest-color-light.webp /static/visitor/assets/interest-people-society.webp; do
  curl -fsS -o /dev/null "http://127.0.0.1:8765$asset"
done
committed=1
echo "Visitor patch deployed. Backup retained at: $backup"
