[CmdletBinding()]
param(
    [string]$HostName = "10.0.0.238",
    [string]$RemoteUser = "super-alex",
    [string]$RemoteRoot = "/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stageRoot = Join-Path $env:TEMP "atlas_response_stability_$timestamp"
$archive = Join-Path $env:TEMP "atlas_response_stability_$timestamp.tar.gz"
$remoteArchive = "/tmp/atlas_response_stability_$timestamp.tar.gz"

$keyCandidates = @(
    "C:\Users\zhupo\Documents\Codex\2026-05-24\files-mentioned-by-the-user-atlas\ssh_key\atlas_codex_jetson",
    "C:\Users\zhupo\Documents\Codex\2026-05-24\files-mentioned-by-the-user-atlas\.atlas_jetson_ed25519"
)
$key = $keyCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $key) {
    throw "ATLAS SSH key not found. Add its path to `$keyCandidates before running this deployment."
}

$files = @(
    "config/settings.yaml",
    "src/atlas/config/settings.py",
    "src/atlas/app/dependency_container.py",
    "src/atlas/dialogue/dialogue_engine.py",
    "src/atlas/dialogue/prompt_builder.py",
    "src/atlas/pipeline/session_runner.py",
    "tests/test_dialogue.py",
    "tests/test_pipeline.py",
    "tests/test_safety.py",
    "tests/test_streaming_dialogue.py",
    "docs/PATCH_HISTORY.md"
)

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

    Write-Host "Uploading the ATLAS response-stability update..."
    scp -i $key $archive "$RemoteUser@$HostName`:$remoteArchive"
    if ($LASTEXITCODE -ne 0) { throw "Upload to the Jetson failed." }

    $remoteCommand = "set -euo pipefail; root='$RemoteRoot'; archive='$remoteArchive'; backup='/tmp/atlas_response_stability_backup_$timestamp'; rollback() { cp -a `"`$backup/config/.`" `"`$root/config/`"; cp -a `"`$backup/src/.`" `"`$root/src/`"; cp -a `"`$backup/tests/.`" `"`$root/tests/`"; cp -a `"`$backup/docs/.`" `"`$root/docs/`" 2>/dev/null || true; systemctl --user restart atlas.service || true; }; mkdir -p `"`$backup/config`" `"`$backup/src/atlas`" `"`$backup/tests`" `"`$backup/docs`"; cp -a `"`$root/config/settings.yaml`" `"`$backup/config/settings.yaml`"; cp -a `"`$root/src/atlas/config`" `"`$backup/src/atlas/config`"; cp -a `"`$root/src/atlas/app`" `"`$backup/src/atlas/app`"; cp -a `"`$root/src/atlas/dialogue`" `"`$backup/src/atlas/dialogue`"; cp -a `"`$root/src/atlas/pipeline`" `"`$backup/src/atlas/pipeline`"; for f in test_dialogue.py test_pipeline.py test_safety.py test_streaming_dialogue.py; do cp -a `"`$root/tests/`$f`" `"`$backup/tests/`$f`"; done; cp -a `"`$root/docs/PATCH_HISTORY.md`" `"`$backup/docs/PATCH_HISTORY.md`" 2>/dev/null || true; tar -xzf `"`$archive`" -C `"`$root`"; cd `"`$root`"; if ! /home/super-alex/atlas/venvs/atlas-school-pilot/bin/python -m pytest tests/test_dialogue.py tests/test_pipeline.py tests/test_safety.py tests/test_streaming_dialogue.py; then rollback; exit 1; fi; if ! systemctl --user restart atlas.service; then rollback; exit 1; fi; ready=0; for attempt in `$(seq 1 60); do if curl -fsS http://127.0.0.1:8765/health > /dev/null; then ready=1; break; fi; sleep 2; done; if [ `"`$ready`" -ne 1 ]; then rollback; exit 1; fi; echo Response-stability update deployed. Backup retained at: `$backup"
    ssh -i $key "$RemoteUser@$HostName" $remoteCommand
    if ($LASTEXITCODE -ne 0) { throw "Jetson validation or restart failed. The remote backup remains available." }

    Write-Host "Done. One full answer now uses one TTS request, and ambiguous artwork references no longer guess a work."
}
finally {
    Remove-Item -LiteralPath $stageRoot -Force -Recurse -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
}
