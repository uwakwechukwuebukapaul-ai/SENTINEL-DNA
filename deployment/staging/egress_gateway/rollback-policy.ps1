param(
  [Parameter(Mandatory=$true)][string]$PolicyFile,
  [Parameter(Mandatory=$true)][string]$RollbackFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $RollbackFile -PathType Leaf)) { throw "GATE4_ROLLBACK_ARTIFACT_MISSING" }
Copy-Item -LiteralPath $RollbackFile -Destination $PolicyFile -Force
Write-Output "GATE4_POLICY_ROLLBACK_RESTORED"
