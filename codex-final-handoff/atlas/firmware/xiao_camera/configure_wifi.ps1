$ErrorActionPreference = "Stop"

$ssid = Read-Host "Enter the 2.4 GHz Wi-Fi name (SSID)"
$securePassword = Read-Host "Enter the Wi-Fi password" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)

try {
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)

    function ConvertTo-CString([string]$Value) {
        return $Value.Replace("\", "\\").Replace('"', '\"')
    }

    $ssidLiteral = ConvertTo-CString $ssid
    $passwordLiteral = ConvertTo-CString $password
    $header = @"
#pragma once

constexpr char WIFI_SSID[] = "$ssidLiteral";
constexpr char WIFI_PASSWORD[] = "$passwordLiteral";
"@

    $path = Join-Path $PSScriptRoot "wifi_secrets.h"
    $utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($path, $header, $utf8WithoutBom)
    Write-Host "Saved local Wi-Fi configuration to $path"
    Write-Host "This file is ignored by Git."
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    $password = $null
}
