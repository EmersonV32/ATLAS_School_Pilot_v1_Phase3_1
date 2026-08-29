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
    "config/settings.yaml",
    "firmware/xiao_camera/xiao_camera.ino",
    "pyproject.toml",
    "requirements.txt",
    "docs/PATCH_HISTORY.md"
)
$trackedTreeFiles = & git -C $repoRoot ls-files -- src/atlas tests data/content_packs/demo_pack
if ($LASTEXITCODE -ne 0) { throw "Could not list tracked runtime files." }
$files += $trackedTreeFiles
$files = @($files | Sort-Object -Unique)

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
paths=(
  data/content_packs/demo_pack
  firmware/xiao_camera/xiao_camera.ino
  pyproject.toml
  requirements.txt
  src/atlas
  tests
  docs/PATCH_HISTORY.md
)
rollback() {
  cp -a "$backup/device_settings.yaml" "$root/config/settings.yaml"
  for path in "${paths[@]}"; do
    rm -rf "$root/$path"
    mkdir -p "$root/$(dirname "$path")"
    cp -a "$backup/files/$path" "$root/$path"
  done
  systemctl --user restart atlas.service || true
}
mkdir -p "$backup/files"
cp -a "$root/config/settings.yaml" "$backup/device_settings.yaml"
for path in "${paths[@]}"; do
  mkdir -p "$backup/files/$(dirname "$path")"
  cp -a "$root/$path" "$backup/files/$path"
done
if ! systemctl --user stop atlas.service; then
  rollback
  exit 1
fi
rm -rf "$root/src/atlas" "$root/tests" "$root/data/content_packs/demo_pack"
tar -xzf "$archive" -C "$root"
cd "$root"
if ! /home/super-alex/atlas/venvs/atlas-school-pilot/bin/python -m pytest; then
  rollback
  exit 1
fi
cp -a "$backup/device_settings.yaml" "$root/config/settings.yaml"
if ! systemctl --user start atlas.service; then
  rollback
  exit 1
fi
ready=0
for attempt in $(seq 1 45); do
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
