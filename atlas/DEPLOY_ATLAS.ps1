[CmdletBinding()]
param(
    [string]$HostName = "10.0.0.238",
    [string]$RemoteUser = "super-alex",
    [string]$RemoteRoot = "/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated",
    [string]$SshKeyPath = $env:ATLAS_SSH_KEY
)

$deployScript = Join-Path $PSScriptRoot "scripts\deploy\DEPLOY_ATLAS_VISITOR_IMPROVEMENTS.ps1"
& $deployScript @PSBoundParameters
