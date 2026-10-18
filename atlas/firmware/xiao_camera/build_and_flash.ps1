param(
    [string]$Port = "COM3",
    [switch]$BuildOnly,
    [switch]$UploadOnly
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$cliRoot = Join-Path $repoRoot ".tools\arduino-cli"
$cli = Join-Path $cliRoot "arduino-cli.exe"
$config = Join-Path $cliRoot "arduino-cli.yaml"
$fqbn = "esp32:esp32:XIAO_ESP32S3:PSRAM=opi,PartitionScheme=max_app_8MB"
$cacheRoot = Join-Path $repoRoot ".tools\atlas-camera-release"
$pointer = Join-Path $cacheRoot "current.json"
$publicFiles = @(
    "xiao_camera.ino", "app_httpd.cpp", "board_config.h", "camera_index.h",
    "camera_pins.h", "camera_profile.h", "school_wifi.h", "school_wifi.cpp",
    "school_wifi_policy.h", "wifi_secrets.h.example", "wifi_school_secrets.h.example",
    "personal_wifi.h", "personal_wifi.cpp", "personal_wifi_policy.h",
    "wifi_personal_secrets.h.example", "camera_timing_policy.h"
)
$privateFiles = @("wifi_secrets.h", "wifi_school_secrets.h", "wifi_personal_secrets.h")

if ($BuildOnly -and $UploadOnly) { throw "Choose BuildOnly or UploadOnly, not both." }

function Assert-RegularPath([string]$Path) {
    $cursor = [IO.Path]::GetFullPath($Path)
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $entry = Get-Item -LiteralPath $cursor -Force
            # OneDrive cloud placeholders are reparse points, not redirected
            # links. Refuse actual junctions/symlinks without rejecting sync.
            if ($entry.LinkType -in @("SymbolicLink", "Junction")) {
                throw "Redirected build/input paths are refused."
            }
        }
        $parent = [IO.Path]::GetDirectoryName($cursor)
        if ($parent -eq $cursor) { break }
        $cursor = $parent
    }
}

function Get-InputState {
    $items = [ordered]@{ fqbn = $fqbn }
    foreach ($name in $publicFiles + $privateFiles) {
        $path = Join-Path $PSScriptRoot $name
        Assert-RegularPath $path
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            $items[$name] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        } elseif ($name -in $publicFiles -or $name -eq "wifi_secrets.h") {
            throw "A required firmware input is missing. No upload performed."
        } else {
            $items[$name] = "absent"
        }
    }
    foreach ($path in @($cli, $config, $PSCommandPath)) {
        Assert-RegularPath $path
        $items[[IO.Path]::GetFileName($path)] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    }
    # Core metadata is non-secret but captured privately with all other diagnostics.
    $coreOutput = (& $cli core list --config-file $config --format json 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "Installed Arduino core metadata unavailable." }
    $metadata = $coreOutput | ConvertFrom-Json
    $installed = @($metadata.platforms | Where-Object { $_.id -eq "esp32:esp32" })
    if ($installed.Count -ne 1 -or -not $installed[0].installed_version) {
        throw "ESP32 core is not installed. No upload performed."
    }
    # The CLI's full metadata includes mutable discovery/index details. Only
    # the installed platform version is part of the build's stable identity.
    $items["installed-core"] = "esp32:esp32@" + $installed[0].installed_version
    return ($items | ConvertTo-Json -Compress -Depth 8)
}

function Assert-PreparedBuild {
    Assert-RegularPath $pointer
    if (-not (Test-Path -LiteralPath $pointer -PathType Leaf)) {
        throw "No prepared camera build. Run with -BuildOnly first."
    }
    $selection = Get-Content -LiteralPath $pointer -Raw | ConvertFrom-Json
    if ($selection.name -notmatch '^[0-9a-f]{32}$') { throw "Invalid private build selection." }
    $script:prepared = Join-Path $cacheRoot $selection.name
    Assert-RegularPath $script:prepared
    $manifestPath = Join-Path $script:prepared "manifest.json"
    Assert-RegularPath $manifestPath
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.inputs -cne (Get-InputState)) {
        throw "Firmware inputs changed since build. Rebuild before uploading."
    }
    if (@($manifest.binaries).Count -lt 3) { throw "Incomplete prepared camera build." }
    foreach ($binary in $manifest.binaries) {
        if ($binary.name -notmatch '^[A-Za-z0-9_.-]+\.bin$') { throw "Invalid binary name." }
        $path = Join-Path (Join-Path $script:prepared "build") $binary.name
        Assert-RegularPath $path
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
            (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -cne $binary.hash) {
            throw "Prepared binary missing or changed. Rebuild before uploading."
        }
    }
}

if (-not (Test-Path $cli)) {
    throw "Arduino CLI is missing at $cli"
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot "wifi_secrets.h"))) {
    throw "Run configure_wifi.ps1 before building."
}

Assert-RegularPath $cacheRoot
if (-not $UploadOnly) {
    $inputs = Get-InputState
    $name = [guid]::NewGuid().ToString("N")
    $prepared = Join-Path $cacheRoot $name
    $sketch = Join-Path $prepared "xiao_camera"
    $build = Join-Path $prepared "build"
    New-Item -ItemType Directory -Path $sketch -Force | Out-Null
    foreach ($file in $publicFiles + $privateFiles) {
        $path = Join-Path $PSScriptRoot $file
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Copy-Item -LiteralPath $path -Destination (Join-Path $sketch $file)
        }
    }
    Write-Host "Compiling private ATLAS camera build. No device will be contacted yet."
    $buildLog = Join-Path $prepared "compile-private.log"
    try {
        & $cli compile --config-file $config --fqbn $fqbn --build-path $build $sketch *> $buildLog
        $compileExit = $LASTEXITCODE
    } catch {
        throw "Compilation failed. Diagnostics retained privately; no upload performed."
    }
    if ($compileExit -ne 0) {
        throw "Compilation failed. Diagnostics retained privately; no upload performed."
    }
    if ($inputs -cne (Get-InputState)) {
        throw "Inputs changed while compiling; prepared build rejected."
    }
    $binaries = @(Get-ChildItem -LiteralPath $build -Filter "*.bin" -File | ForEach-Object {
        @{ name = $_.Name; hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
    })
    if ($binaries.Count -lt 3) { throw "Compilation did not produce a complete binary set." }
    $manifest = @{ inputs = $inputs; binaries = $binaries }
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText((Join-Path $prepared "manifest.json"), ($manifest | ConvertTo-Json -Depth 8), $encoding)
    [IO.File]::WriteAllText($pointer, (@{ name = $name } | ConvertTo-Json), $encoding)
    Write-Host "Prepared private camera build. Do not share its binaries, headers or logs."
}

Assert-PreparedBuild
if ($BuildOnly) {
    Write-Host "Build-only complete. No camera flashed. Use -UploadOnly -Port <verified port> on arrival."
    exit 0
}
Write-Host "Uploading firmware to $Port..."
$build = Join-Path $prepared "build"
$uploadLog = Join-Path $prepared "upload-private.log"
try {
    & $cli upload --config-file $config --port $Port --fqbn $fqbn --input-dir $build (Join-Path $prepared "xiao_camera") *> $uploadLog
    $uploadExit = $LASTEXITCODE
} catch {
    throw "Upload failed. Diagnostics retained privately; verify USB locally."
}
if ($uploadExit -ne 0) {
    throw "Upload failed. Diagnostics retained privately; verify USB port/bootloader locally."
}

Write-Host "Upload complete. The camera is restarting."
