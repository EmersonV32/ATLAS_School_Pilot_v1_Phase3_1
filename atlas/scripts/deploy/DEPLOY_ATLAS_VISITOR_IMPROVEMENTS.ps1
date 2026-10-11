[CmdletBinding()]
param(
    [string]$HostName = "10.0.0.238",
    [string]$RemoteUser = "super-alex",
    [string]$RemoteRoot = "/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated",
    [string]$SshKeyPath = $env:ATLAS_SSH_KEY,
    [string]$RemotePython = "/home/super-alex/atlas/venvs/atlas-school-pilot/bin/python",
    [string]$YoloCheckpoint = "models/atlas_yolo.pt",
    # Optional engine already exported and checked ON THIS Jetson, never a laptop engine.
    [string]$StagedRuntimeRoot = "",
    [switch]$PrepareOnly,
    [string]$PreparedArchivePath = ""
)

$ErrorActionPreference = "Stop"
foreach ($remotePath in @($RemoteRoot, $RemotePython)) {
    if ($remotePath -notmatch "^/[A-Za-z0-9_./-]+$") { throw "Remote paths must be absolute POSIX paths without shell metacharacters." }
}
if ($StagedRuntimeRoot -and $StagedRuntimeRoot -notmatch '^/tmp/atlas_v6_preflight_[A-Za-z0-9_-]+$') { throw 'Staged runtime must be an explicit Jetson /tmp/atlas_v6_preflight_* directory.' }
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$timestamp = (Get-Date -Format "yyyyMMdd_HHmmss") + "_" + [Guid]::NewGuid().ToString("N").Substring(0, 8)
$stageRoot = Join-Path $env:TEMP "atlas_visitor_patch_$timestamp"
$archive = Join-Path $env:TEMP "atlas_visitor_patch_$timestamp.tar.gz"
$remoteArchive = "/tmp/atlas_visitor_patch_$timestamp.tar.gz"

$checkpointSource = if ([IO.Path]::IsPathRooted($YoloCheckpoint)) { $YoloCheckpoint } else { Join-Path $repoRoot $YoloCheckpoint }
$checkpointSource = (Resolve-Path -LiteralPath $checkpointSource).Path
if ([IO.Path]::GetExtension($checkpointSource) -ne ".pt") { throw "YOLO source must be a portable .pt checkpoint, not a target-specific engine." }

if (-not $PrepareOnly) {
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
}

$files = @(
    # Keep the Jetson's deployment-specific config/settings.yaml in place.
    # It contains LAN binding and admin-auth policy that differ from dev defaults.
    "config/settings.yaml",
    "config/artwork_labels.yaml",
    "firmware/xiao_camera/xiao_camera.ino",
    "models/atlas_yolo.pt",
    "models/manifest.sha256",
    "models/README.md",
    "models/releases/2026-09-28-yolo26n-atlas-v6/best.pt",
    "models/releases/2026-09-07-camera-domain-rollback/atlas_yolo.pt",
    "models/releases/2026-09-07-camera-domain-rollback/manifest.sha256",
    "models/releases/2026-09-07-camera-domain-rollback/README.md",
    "artwork-source/mona-lisa.png",
    "artwork-source/great-wave.png",
    "pyproject.toml",
    "requirements.txt",
    "scripts/atlas.service",
    "scripts/check_arducam.sh",
    "scripts/diagnose_yolo_dataset.py",
    "scripts/diagnose_yolo_images.py",
    "scripts/export_tensorrt.py",
    "scripts/inspect_yolo_results.py",
    "scripts/smoke_yolo_runtime.py",
    "scripts/run_deployment_pytest.py",
    "scripts/promote_staged_engine.py",
    "scripts/build_phone_yolo_dataset.py",
    "training/prepare_artwork_dataset_v5.py",
    "training/handoff/train.py",
    "scripts/restore_models.sh",
    "scripts/deploy/apply_visitor_patch.sh",
    "scripts/install_user_service.sh",
    "scripts/validate_artwork_release.py",
    "scripts/verify_yolo_checkpoint.py",
    "docs/PATCH_HISTORY.md",
    "docs/2026-10-04_FIXES_AND_V6_UPDATE.md",
    "docs/2026-10-04_V6_LOCAL_INTEGRATION.md"
)
$trackedTreeFiles = & git -C $repoRoot ls-files --cached --others --exclude-standard -- src/atlas tests data/content_packs/demo_pack
if ($LASTEXITCODE -ne 0) { throw "Could not list tracked runtime files." }
$files += $trackedTreeFiles
$files = @($files | Sort-Object -Unique)

New-Item -ItemType Directory -Path $stageRoot | Out-Null
try {
    foreach ($relativePath in $files) {
        $source = Join-Path $repoRoot $relativePath
        if (-not (Test-Path -LiteralPath $source)) { throw "Required patch file is missing: $relativePath" }
        $destination = Join-Path $stageRoot $relativePath
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }

    # Select the reviewed checkpoint in the bundle, never in the working runtime.
    Copy-Item -LiteralPath $checkpointSource -Destination (Join-Path $stageRoot "models/atlas_yolo.pt") -Force
    $checkpointHash = (Get-FileHash -LiteralPath (Join-Path $stageRoot "models/atlas_yolo.pt") -Algorithm SHA256).Hash.ToLowerInvariant()
    [IO.File]::WriteAllText((Join-Path $stageRoot "models/manifest.sha256"), "$checkpointHash  atlas_yolo.pt`n", [Text.UTF8Encoding]::new($false))

    tar -czf $archive -C $stageRoot .
    if ($LASTEXITCODE -ne 0) { throw "Could not build the deployment archive." }

    if ($PrepareOnly) {
        if (-not $PreparedArchivePath) { $PreparedArchivePath = Join-Path $repoRoot "atlas_visitor_patch_$timestamp.tar.gz" }
        $PreparedArchivePath = [IO.Path]::GetFullPath($PreparedArchivePath)
        if (Test-Path -LiteralPath $PreparedArchivePath) { throw "Prepared archive already exists; refusing to overwrite: $PreparedArchivePath" }
        Copy-Item -LiteralPath $archive -Destination $PreparedArchivePath
        Write-Host "Prepared locally (not uploaded or deployed): $PreparedArchivePath"
        Write-Host "Checkpoint SHA-256: $checkpointHash"
        return
    }

    Write-Host "Uploading the visitor dashboard patch to the existing ATLAS service..."
    scp -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes -i $key $archive "$RemoteUser@$HostName`:$remoteArchive"
    if ($LASTEXITCODE -ne 0) { throw "Upload to the Jetson failed." }

    $remoteCommand = (Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot "apply_visitor_patch.sh")).Replace('__ROOT__', $RemoteRoot).Replace('__ARCHIVE__', $remoteArchive).Replace('__STAMP__', $timestamp).Replace('__PYTHON__', $RemotePython).Replace('__STAGED_ROOT__', $StagedRuntimeRoot)
    # PowerShell scripts may be checked out with CRLF, but the remote command is
    # parsed by Bash. Normalize it explicitly so `set -euo pipefail` is valid.
    $remoteCommand = $remoteCommand.Replace("`r`n", "`n")
    ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes -i $key "$RemoteUser@$HostName" $remoteCommand
    if ($LASTEXITCODE -ne 0) { throw "Jetson validation or restart failed. The remote backup remains available." }

    Write-Host "Done. Test visitor: http://$HostName`:8765/"
    Write-Host "Done. Test admin:   http://$HostName`:8765/admin"
}
finally {
    # Resolve/validate exact temporary targets before recursive cleanup on Windows.
    $taskTempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    foreach ($taskTemporaryPath in @($stageRoot, $archive)) {
        $taskResolvedPath = [IO.Path]::GetFullPath($taskTemporaryPath)
        if (-not $taskResolvedPath.StartsWith($taskTempRoot, [StringComparison]::OrdinalIgnoreCase)) { throw "Unsafe cleanup target: $taskResolvedPath" }
    }
    Remove-Item -LiteralPath $stageRoot -Force -Recurse -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
}
