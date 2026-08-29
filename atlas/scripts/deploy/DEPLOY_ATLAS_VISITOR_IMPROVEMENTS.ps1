[CmdletBinding()]
param(
    [string]$HostName = "10.0.0.238",
    [string]$RemoteUser = "super-alex",
    [string]$RemoteRoot = "/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated",
    [string]$SshKeyPath = $env:ATLAS_SSH_KEY
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stageRoot = Join-Path $env:TEMP "atlas_visitor_patch_$timestamp"
$archive = Join-Path $env:TEMP "atlas_visitor_patch_$timestamp.tar.gz"
$remoteArchive = "/tmp/atlas_visitor_patch_$timestamp.tar.gz"

$keyCandidates = @(
    $SshKeyPath,
    (Join-Path $HOME ".ssh\atlas_codex_jetson"),
    "C:\Users\zhupo\Documents\Codex\2026-05-24\files-mentioned-by-the-user-atlas\ssh_key\atlas_codex_jetson",
    "C:\Users\zhupo\Documents\Codex\2026-05-24\files-mentioned-by-the-user-atlas\.atlas_jetson_ed25519"
)
$key = $keyCandidates |
    Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
    Select-Object -First 1
if (-not $key) {
    throw "ATLAS SSH key not found. Pass -SshKeyPath or set ATLAS_SSH_KEY."
}

$files = @(
    # Keep the Jetson's deployment-specific config/settings.yaml in place.
    # It contains LAN binding and admin-auth policy that differ from dev defaults.
    "src/atlas/dashboard/templates/index.html",
    "src/atlas/dashboard/templates/admin.html",
    "src/atlas/dashboard/static/visitor.js",
    "src/atlas/dashboard/static/visitor.css",
    "src/atlas/dashboard/static/service-worker.js",
    "src/atlas/dashboard/static/admin.js",
    "src/atlas/dashboard/static/style.css",
    "src/atlas/dashboard/static/manifest.webmanifest",
    "src/atlas/dashboard/visitor_service.py",
    "src/atlas/dashboard/visitor_schemas.py",
    "src/atlas/dashboard/api.py",
    "src/atlas/dashboard/runtime_service.py",
    "src/atlas/dashboard/schemas.py",
    "src/atlas/app/dependency_container.py",
    "src/atlas/app/device_runtime.py",
    "src/atlas/app/preflight.py",
    "src/atlas/audio/cartesia_tts.py",
    "src/atlas/audio/deepgram_stt.py",
    "src/atlas/audio/fallback.py",
    "src/atlas/audio/whisper_stt.py",
    "src/atlas/config/loader.py",
    "src/atlas/config/settings.py",
    "src/atlas/dialogue/dialogue_engine.py",
    "src/atlas/dialogue/gemini_client.py",
    "src/atlas/dialogue/openai_compatible_client.py",
    "src/atlas/dialogue/prompt_builder.py",
    "src/atlas/dialogue/safety_filter.py",
    "src/atlas/models/enums.py",
    "src/atlas/pipeline/session_runner.py",
    "src/atlas/safety/prompt_injection_filter.py",
    "src/atlas/vision/camera_source.py",
    "data/content_packs/demo_pack/artworks/girl_with_a_pearl_earring.json",
    "data/content_packs/demo_pack/artworks/great_wave_off_kanagawa.json",
    "data/content_packs/demo_pack/artworks/mona_lisa.json",
    "data/content_packs/demo_pack/artworks/sunflowers.json",
    "data/content_packs/demo_pack/artworks/tutankhamun_mask.json",
    "data/content_packs/demo_pack/manifest.json",
    "firmware/xiao_camera/xiao_camera.ino",
    "pyproject.toml",
    "requirements.txt",
    "tests/test_camera_source.py",
    "tests/test_visitor_dashboard.py",
    "tests/test_cloud_speech.py",
    "tests/test_dashboard_api.py",
    "tests/test_device_integrations.py",
    "tests/test_dialogue.py",
    "tests/test_fallback_tts.py",
    "tests/test_headset_button.py",
    "tests/test_openai_compatible_client.py",
    "tests/test_safety.py",
    "docs/PATCH_HISTORY.md"
)
$files += Get-ChildItem -LiteralPath (Join-Path $repoRoot "src/atlas/dashboard/static/visitor") -File -Recurse |
    ForEach-Object { $_.FullName.Substring($repoRoot.Length + 1).Replace("\", "/") }

New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null
try {
    foreach ($relativePath in $files) {
        $source = Join-Path $repoRoot $relativePath
        if (-not (Test-Path -LiteralPath $source)) { throw "Required patch file is missing: $relativePath" }
        $destination = Join-Path $stageRoot $relativePath
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }

    tar -czf $archive -C $stageRoot .
    if ($LASTEXITCODE -ne 0) { throw "Could not build the deployment archive." }

    Write-Host "Uploading the visitor dashboard patch to the existing ATLAS service..."
    scp -i $key $archive "$RemoteUser@$HostName`:$remoteArchive"
    if ($LASTEXITCODE -ne 0) { throw "Upload to the Jetson failed." }

    $remoteCommand = @'
set -euo pipefail
root='__ROOT__'
archive='__ARCHIVE__'
backup='/tmp/atlas_visitor_backup___STAMP__'
files=(
  data/content_packs/demo_pack/artworks/girl_with_a_pearl_earring.json
  data/content_packs/demo_pack/artworks/great_wave_off_kanagawa.json
  data/content_packs/demo_pack/artworks/mona_lisa.json
  data/content_packs/demo_pack/artworks/sunflowers.json
  data/content_packs/demo_pack/artworks/tutankhamun_mask.json
  data/content_packs/demo_pack/manifest.json
  firmware/xiao_camera/xiao_camera.ino
  pyproject.toml
  requirements.txt
  src/atlas/app/dependency_container.py
  src/atlas/app/device_runtime.py
  src/atlas/app/preflight.py
  src/atlas/audio/cartesia_tts.py
  src/atlas/audio/deepgram_stt.py
  src/atlas/audio/fallback.py
  src/atlas/audio/whisper_stt.py
  src/atlas/config/loader.py
  src/atlas/config/settings.py
  src/atlas/dashboard/schemas.py
  src/atlas/dialogue/dialogue_engine.py
  src/atlas/dialogue/gemini_client.py
  src/atlas/dialogue/openai_compatible_client.py
  src/atlas/dialogue/prompt_builder.py
  src/atlas/dialogue/safety_filter.py
  src/atlas/models/enums.py
  src/atlas/pipeline/session_runner.py
  src/atlas/safety/prompt_injection_filter.py
  src/atlas/vision/camera_source.py
  tests/test_camera_source.py
  tests/test_visitor_dashboard.py
  tests/test_cloud_speech.py
  tests/test_dashboard_api.py
  tests/test_device_integrations.py
  tests/test_dialogue.py
  tests/test_fallback_tts.py
  tests/test_headset_button.py
  tests/test_openai_compatible_client.py
  tests/test_safety.py
  docs/PATCH_HISTORY.md
)
rollback() {
  cp -a "$backup/dashboard/." "$root/src/atlas/dashboard/"
  cp -a "$backup/files/." "$root/"
  systemctl --user restart atlas.service || true
}
mkdir -p "$backup/files"
cp -a "$root/src/atlas/dashboard" "$backup/dashboard"
for file in "${files[@]}"; do
  mkdir -p "$backup/files/$(dirname "$file")"
  cp -a "$root/$file" "$backup/files/$file"
done
tar -xzf "$archive" -C "$root"
cd "$root"
if ! /home/super-alex/atlas/venvs/atlas-school-pilot/bin/python -m pytest; then
  rollback
  exit 1
fi
if ! systemctl --user restart atlas.service; then
  rollback
  exit 1
fi
ready=0
for attempt in $(seq 1 25); do
  if curl -fsS http://127.0.0.1:8765/health > /dev/null; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  rollback
  exit 1
fi
for asset in /static/visitor/assets/atlas-logo-v2.webp /static/visitor/assets/gallery-mona-lisa.webp /static/visitor/assets/gallery-great-wave.webp /static/visitor/assets/gallery-ambassadors.webp /static/visitor/assets/interest-stories.webp /static/visitor/assets/interest-technique.webp /static/visitor/assets/interest-symbols.webp /static/visitor/assets/interest-history.webp /static/visitor/assets/interest-color-light.webp /static/visitor/assets/interest-people-society.webp; do
  curl -fsS -o /dev/null "http://127.0.0.1:8765$asset" || { rollback; exit 1; }
done
echo "Visitor patch deployed. Backup retained at: $backup"
'@.Replace('__ROOT__', $RemoteRoot).Replace('__ARCHIVE__', $remoteArchive).Replace('__STAMP__', $timestamp)
    ssh -i $key "$RemoteUser@$HostName" $remoteCommand
    if ($LASTEXITCODE -ne 0) { throw "Jetson validation or restart failed. The remote backup remains available." }

    Write-Host "Done. Test visitor: http://$HostName`:8765/"
    Write-Host "Done. Test admin:   http://$HostName`:8765/admin"
}
finally {
    Remove-Item -LiteralPath $stageRoot -Force -Recurse -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
}
