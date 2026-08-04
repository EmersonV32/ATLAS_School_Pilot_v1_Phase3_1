$ErrorActionPreference = "Stop"

$sourceRoot = Join-Path $PSScriptRoot "ATLAS_School_Pilot_v1_Phase3_1\atlas"
$keyPath = Join-Path $PSScriptRoot "ssh_key\atlas_codex_jetson"
$target = "super-alex@10.0.0.238"
$remoteRepo = "/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated"
$remotePython = "/home/super-alex/atlas/venvs/atlas-school-pilot/bin/python"
$archive = Join-Path $env:TEMP "atlas_logging_update.tar.gz"

$files = @(
    "config/settings.yaml",
    "src/atlas/app/dependency_container.py",
    "src/atlas/app/device_runtime.py",
    "src/atlas/app/headset_button.py",
    "src/atlas/app/main.py",
    "src/atlas/audio/cartesia_tts.py",
    "src/atlas/audio/deepgram_stt.py",
    "src/atlas/audio/devices.py",
    "src/atlas/audio/fallback.py",
    "src/atlas/config/loader.py",
    "src/atlas/config/settings.py",
    "src/atlas/dashboard/runtime_service.py",
    "src/atlas/dashboard/schemas.py",
    "src/atlas/dashboard/static/admin.js",
    "src/atlas/dashboard/templates/admin.html",
    "src/atlas/dialogue/gemini_client.py",
    "src/atlas/pipeline/session_runner.py",
    "tests/test_cloud_speech.py",
    "tests/test_dashboard_api.py",
    "tests/test_dashboard_privacy.py",
    "tests/test_device_integrations.py",
    "tests/test_pipeline.py"
)

if (-not (Test-Path -LiteralPath $sourceRoot)) {
    throw "ATLAS source folder not found: $sourceRoot"
}
if (-not (Test-Path -LiteralPath $keyPath)) {
    throw "Jetson SSH key not found: $keyPath"
}

try {
    Write-Host "Packing the tested logging update..."
    tar -czf $archive -C $sourceRoot @files
    if ($LASTEXITCODE -ne 0) { throw "Could not create update archive" }

    Write-Host "Transferring update to the Jetson..."
    scp -i $keyPath $archive "${target}:/tmp/atlas_logging_update.tar.gz"
    if ($LASTEXITCODE -ne 0) { throw "SCP transfer failed" }

    $remoteScript = @'
set -euo pipefail
repo="/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated"
python="/home/super-alex/atlas/venvs/atlas-school-pilot/bin/python"
archive="/tmp/atlas_logging_update.tar.gz"
backup="/tmp/atlas_logging_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
restarted=0
files=(
  config/settings.yaml
  src/atlas/app/dependency_container.py
  src/atlas/app/device_runtime.py
  src/atlas/app/main.py
  src/atlas/audio/cartesia_tts.py
  src/atlas/audio/deepgram_stt.py
  src/atlas/audio/devices.py
  src/atlas/audio/fallback.py
  src/atlas/config/loader.py
  src/atlas/config/settings.py
  src/atlas/dashboard/runtime_service.py
  src/atlas/dashboard/schemas.py
  src/atlas/dashboard/static/admin.js
  src/atlas/dashboard/templates/admin.html
  src/atlas/dialogue/gemini_client.py
  src/atlas/pipeline/session_runner.py
  tests/test_cloud_speech.py
  tests/test_dashboard_api.py
  tests/test_dashboard_privacy.py
  tests/test_device_integrations.py
  tests/test_pipeline.py
)

cd "$repo"
tar -czf "$backup" "${files[@]}"
tar -xzf "$archive"

rollback() {
  trap - ERR
  echo "Validation failed. Restoring $backup"
  rm -f src/atlas/app/headset_button.py
  tar -xzf "$backup" -C "$repo"
  if [ "$restarted" -eq 1 ]; then
    systemctl --user restart atlas.service
  fi
}
trap rollback ERR

"$python" -m compileall -q src tests
"$python" -m pytest -q \
  tests/test_cloud_speech.py \
  tests/test_pipeline.py \
  tests/test_dashboard_api.py \
  tests/test_dashboard_privacy.py \
  tests/test_device_integrations.py

systemctl --user restart atlas.service
restarted=1
sleep 5
systemctl --user is-active --quiet atlas.service
for _attempt in $(seq 1 60); do
  if curl --fail --silent http://127.0.0.1:8765/health >/dev/null; then
    break
  fi
  systemctl --user is-active --quiet atlas.service
  sleep 2
done
curl --fail --silent --show-error http://127.0.0.1:8765/health >/dev/null
trap - ERR

echo "ATLAS logging update deployed successfully."
echo "Rollback backup retained at: $backup"
tail -n 60 data/logs/atlas-runtime.log
'@

    Write-Host "Testing and restarting ATLAS on the Jetson..."
    $remoteScript = $remoteScript -replace "`r`n", "`n"
    $remoteScript | ssh -i $keyPath $target "bash -s"
    if ($LASTEXITCODE -ne 0) { throw "Jetson validation or restart failed" }
}
finally {
    if (Test-Path -LiteralPath $archive) {
        Remove-Item -LiteralPath $archive -Force
    }
}
