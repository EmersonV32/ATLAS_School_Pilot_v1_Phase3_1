[CmdletBinding()]
param(
    [string]$HostName = "10.0.0.238",
    [string]$RemoteUser = "super-alex",
    [string]$RemoteRoot = "/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stageRoot = Join-Path $env:TEMP "atlas_gemini_policy_$timestamp"
$archive = Join-Path $env:TEMP "atlas_gemini_policy_$timestamp.tar.gz"
$remoteArchive = "/tmp/atlas_gemini_policy_$timestamp.tar.gz"

$keyCandidates = @(
    "C:\Users\zhupo\Documents\Codex\2026-05-24\files-mentioned-by-the-user-atlas\ssh_key\atlas_codex_jetson",
    "C:\Users\zhupo\Documents\Codex\2026-05-24\files-mentioned-by-the-user-atlas\.atlas_jetson_ed25519"
)
$key = $keyCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $key) {
    throw "ATLAS SSH key not found. Add its path to `$keyCandidates before running this deployment."
}

$files = @(
    "src/atlas/dialogue/prompt_builder.py",
    "src/atlas/dialogue/dialogue_engine.py",
    "tests/test_dialogue.py",
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

    Write-Host "Uploading the Gemini general-knowledge policy update..."
    scp -i $key $archive "$RemoteUser@$HostName`:$remoteArchive"
    if ($LASTEXITCODE -ne 0) { throw "Upload to the Jetson failed." }

    $remoteCommand = "set -euo pipefail; root='$RemoteRoot'; archive='$remoteArchive'; backup='/tmp/atlas_gemini_policy_backup_$timestamp'; rollback() { cp -a `"`$backup/prompt_builder.py`" `"`$root/src/atlas/dialogue/prompt_builder.py`"; cp -a `"`$backup/dialogue_engine.py`" `"`$root/src/atlas/dialogue/dialogue_engine.py`"; cp -a `"`$backup/test_dialogue.py`" `"`$root/tests/test_dialogue.py`"; cp -a `"`$backup/test_safety.py`" `"`$root/tests/test_safety.py`"; cp -a `"`$backup/test_streaming_dialogue.py`" `"`$root/tests/test_streaming_dialogue.py`"; cp -a `"`$backup/PATCH_HISTORY.md`" `"`$root/docs/PATCH_HISTORY.md`" 2>/dev/null || true; systemctl --user restart atlas.service || true; }; mkdir -p `"`$backup`"; cp -a `"`$root/src/atlas/dialogue/prompt_builder.py`" `"`$backup/prompt_builder.py`"; cp -a `"`$root/src/atlas/dialogue/dialogue_engine.py`" `"`$backup/dialogue_engine.py`"; cp -a `"`$root/tests/test_dialogue.py`" `"`$backup/test_dialogue.py`"; cp -a `"`$root/tests/test_safety.py`" `"`$backup/test_safety.py`"; cp -a `"`$root/tests/test_streaming_dialogue.py`" `"`$backup/test_streaming_dialogue.py`"; cp -a `"`$root/docs/PATCH_HISTORY.md`" `"`$backup/PATCH_HISTORY.md`" 2>/dev/null || true; tar -xzf `"`$archive`" -C `"`$root`"; cd `"`$root`"; if ! /home/super-alex/atlas/venvs/atlas-school-pilot/bin/python -m pytest tests/test_dialogue.py tests/test_safety.py tests/test_streaming_dialogue.py; then rollback; exit 1; fi; if ! systemctl --user restart atlas.service; then rollback; exit 1; fi; ready=0; for attempt in `$(seq 1 25); do if curl -fsS http://127.0.0.1:8765/health > /dev/null; then ready=1; break; fi; sleep 2; done; if [ `"`$ready`" -ne 1 ]; then rollback; exit 1; fi; echo Gemini policy deployed. Backup retained at: `$backup"
    ssh -i $key "$RemoteUser@$HostName" $remoteCommand
    if ($LASTEXITCODE -ne 0) { throw "Jetson validation or restart failed. The remote backup remains available." }

    Write-Host "Done. Gemini is now answering normally when RAG has no usable match."
}
finally {
    Remove-Item -LiteralPath $stageRoot -Force -Recurse -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
}
