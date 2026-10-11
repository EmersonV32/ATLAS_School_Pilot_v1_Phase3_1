# Compile the real firmware only with public synthetic credentials, never flash.
$ErrorActionPreference = "Stop"
$project = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repo = (Resolve-Path (Join-Path $project "..")).Path
$cli = Join-Path $repo ".tools\arduino-cli\arduino-cli.exe"
$config = Join-Path $repo ".tools\arduino-cli\arduino-cli.yaml"
$source = Join-Path $project "firmware\xiao_camera"
$fixtures = Join-Path $project "tests\fixtures"
$staging = Join-Path ([IO.Path]::GetTempPath()) ("atlas_school_build_" + [guid]::NewGuid().ToString("N"))
$publicFiles = @(
    "xiao_camera.ino", "app_httpd.cpp", "board_config.h", "camera_index.h",
    "camera_pins.h", "camera_profile.h", "school_wifi.h", "school_wifi.cpp",
    "school_wifi_policy.h", "wifi_school_secrets.h.example"
)
foreach ($variant in @("hotspot-only", "school-unverified", "school-verified")) {
    $sketch = Join-Path $staging "$variant\xiao_camera"
    New-Item -ItemType Directory -Path $sketch | Out-Null
    foreach ($name in $publicFiles) {
        Copy-Item -LiteralPath (Join-Path $source $name) -Destination (Join-Path $sketch $name)
    }
    Copy-Item -LiteralPath (Join-Path $source "wifi_secrets.h.example") -Destination (Join-Path $sketch "wifi_secrets.h")
    Copy-Item -LiteralPath (Join-Path $fixtures "school_wifi_policy_checks.cpp") -Destination (Join-Path $sketch "policy_checks.cpp")
    if ($variant -ne "hotspot-only") {
        $fixture = if ($variant -eq "school-unverified") { "wifi_school_unverified.h" } else { "wifi_school_verified.h" }
        Copy-Item -LiteralPath (Join-Path $fixtures $fixture) -Destination (Join-Path $sketch "wifi_school_secrets.h")
    }
    Write-Host "Compiling synthetic variant: $variant"
    & $cli compile --config-file $config --fqbn "esp32:esp32:XIAO_ESP32S3:PSRAM=opi,PartitionScheme=max_app_8MB" --build-path (Join-Path $staging "$variant\build") $sketch
    if ($LASTEXITCODE -ne 0) { throw "Synthetic firmware compile failed: $variant" }
}
Write-Host "All three synthetic firmware variants compiled. No hardware flashed."
Write-Host "Synthetic build artifacts retained at: $staging"
