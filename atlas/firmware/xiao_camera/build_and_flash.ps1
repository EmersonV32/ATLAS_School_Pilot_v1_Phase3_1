param(
    [string]$Port = "COM3"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$workspaceRoot = Split-Path $repoRoot -Parent
$cliRoot = Join-Path $workspaceRoot ".tools\arduino-cli"
$cli = Join-Path $cliRoot "arduino-cli.exe"
$config = Join-Path $cliRoot "arduino-cli.yaml"
$secrets = Join-Path $PSScriptRoot "wifi_secrets.h"
$fqbn = "esp32:esp32:XIAO_ESP32S3:PSRAM=opi,PartitionScheme=max_app_8MB"

if (-not (Test-Path $cli)) {
    throw "Arduino CLI is missing at $cli"
}
if (-not (Test-Path $secrets)) {
    throw "Run configure_wifi.ps1 before building."
}

Write-Host "Compiling ATLAS XIAO camera firmware..."
& $cli compile --config-file $config --fqbn $fqbn $PSScriptRoot
if ($LASTEXITCODE -ne 0) {
    throw "Firmware compilation failed."
}

Write-Host "Uploading firmware to $Port..."
& $cli upload --config-file $config --port $Port --fqbn $fqbn $PSScriptRoot
if ($LASTEXITCODE -ne 0) {
    throw "Firmware upload failed."
}

Write-Host "Upload complete. The camera is restarting."
