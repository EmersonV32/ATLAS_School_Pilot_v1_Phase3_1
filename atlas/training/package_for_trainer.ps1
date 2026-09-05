param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "outgoing")
)

$ErrorActionPreference = "Stop"

$sourceDataset = Join-Path $PSScriptRoot "datasets\atlas-artworks-v4"
$handoffSource = Join-Path $PSScriptRoot "handoff"
$packageName = "ATLAS-artwork-detector-training-v4"
$packageRoot = Join-Path $OutputDirectory $packageName
$archive = Join-Path $OutputDirectory "$packageName.zip"

if (!(Test-Path -LiteralPath $sourceDataset)) {
    throw "Prepared dataset not found: $sourceDataset"
}
if (Test-Path -LiteralPath $packageRoot) {
    throw "Package directory already exists: $packageRoot. Rename or remove it deliberately before rebuilding."
}
if (Test-Path -LiteralPath $archive) {
    throw "Package archive already exists: $archive. Rename or remove it deliberately before rebuilding."
}

New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $sourceDataset "train") -Destination $packageRoot -Recurse
Copy-Item -LiteralPath (Join-Path $sourceDataset "valid") -Destination $packageRoot -Recurse
Copy-Item -LiteralPath (Join-Path $sourceDataset "test") -Destination $packageRoot -Recurse
Copy-Item -LiteralPath (Join-Path $handoffSource "README.md") -Destination $packageRoot
Copy-Item -LiteralPath (Join-Path $handoffSource "requirements.txt") -Destination $packageRoot
Copy-Item -LiteralPath (Join-Path $handoffSource "train.py") -Destination $packageRoot
New-Item -ItemType Directory -Path (Join-Path $packageRoot "dataset") | Out-Null
Copy-Item -LiteralPath (Join-Path $handoffSource "data.yaml.template") -Destination (Join-Path $packageRoot "dataset")
Rename-Item -LiteralPath (Join-Path $packageRoot "dataset\data.yaml.template") -NewName "data.yaml"

Get-ChildItem -LiteralPath $packageRoot -Recurse -File |
    Get-FileHash -Algorithm SHA256 |
    ForEach-Object { "{0}  {1}" -f $_.Hash, $_.Path.Substring($packageRoot.Length + 1) } |
    Set-Content -LiteralPath (Join-Path $packageRoot "SHA256SUMS.txt") -Encoding ascii

Compress-Archive -LiteralPath $packageRoot -DestinationPath $archive -CompressionLevel Optimal
Write-Output "Created training handoff: $archive"
