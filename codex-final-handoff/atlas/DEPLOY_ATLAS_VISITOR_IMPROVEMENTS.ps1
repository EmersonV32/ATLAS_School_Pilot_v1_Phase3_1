[CmdletBinding()]
param(
    [string]$HostName = "10.0.0.238",
    [string]$RemoteUser = "super-alex",
    [string]$RemoteRoot = "/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stageRoot = Join-Path $env:TEMP "atlas_visitor_patch_$timestamp"
$archive = Join-Path $env:TEMP "atlas_visitor_patch_$timestamp.tar.gz"
$remoteArchive = "/tmp/atlas_visitor_patch_$timestamp.tar.gz"

$keyCandidates = @(
    "C:\Users\zhupo\Documents\Codex\2026-05-24\files-mentioned-by-the-user-atlas\ssh_key\atlas_codex_jetson",
    "C:\Users\zhupo\Documents\Codex\2026-05-24\files-mentioned-by-the-user-atlas\.atlas_jetson_ed25519"
)
$key = $keyCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $key) {
    throw "ATLAS SSH key not found. Add its path to `$keyCandidates before running this deployment."
}

$files = @(
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
    "tests/test_visitor_dashboard.py",
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

    $remoteCommand = "set -euo pipefail; root='$RemoteRoot'; archive='$remoteArchive'; backup='/tmp/atlas_visitor_backup_$timestamp'; rollback() { cp -a `"`$backup/dashboard/.`" `"`$root/src/atlas/dashboard/`"; cp -a `"`$backup/test_visitor_dashboard.py`" `"`$root/tests/test_visitor_dashboard.py`"; if [ -f `"`$backup/docs/PATCH_HISTORY.md`" ]; then cp -a `"`$backup/docs/PATCH_HISTORY.md`" `"`$root/docs/PATCH_HISTORY.md`"; fi; systemctl --user restart atlas.service || true; }; mkdir -p `"`$backup`"; cp -a `"`$root/src/atlas/dashboard`" `"`$backup/dashboard`"; cp -a `"`$root/tests/test_visitor_dashboard.py`" `"`$backup/test_visitor_dashboard.py`"; mkdir -p `"`$backup/docs`"; cp -a `"`$root/docs/PATCH_HISTORY.md`" `"`$backup/docs/PATCH_HISTORY.md`" 2>/dev/null || true; tar -xzf `"`$archive`" -C `"`$root`"; cd `"`$root`"; if ! /home/super-alex/atlas/venvs/atlas-school-pilot/bin/python -m pytest tests/test_visitor_dashboard.py; then rollback; exit 1; fi; if ! systemctl --user restart atlas.service; then rollback; exit 1; fi; ready=0; for attempt in `$(seq 1 25); do if curl -fsS http://127.0.0.1:8765/health > /dev/null; then ready=1; break; fi; sleep 2; done; if [ `"`$ready`" -ne 1 ]; then rollback; exit 1; fi; for asset in /static/visitor/assets/atlas-logo-v2.webp /static/visitor/assets/expertise-mona.webp /static/visitor/assets/stories.svg; do curl -fsS -o /dev/null `"http://127.0.0.1:8765`$asset`" || { rollback; exit 1; }; done; echo Visitor patch deployed. Backup retained at: `$backup"
    ssh -i $key "$RemoteUser@$HostName" $remoteCommand
    if ($LASTEXITCODE -ne 0) { throw "Jetson validation or restart failed. The remote backup remains available." }

    Write-Host "Done. Test visitor: http://$HostName`:8765/"
    Write-Host "Done. Test admin:   http://$HostName`:8765/admin"
}
finally {
    Remove-Item -LiteralPath $stageRoot -Force -Recurse -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
}
