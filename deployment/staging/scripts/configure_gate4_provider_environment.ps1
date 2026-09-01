[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ApprovedRuntimeModule,

    [Parameter(Mandatory = $true)]
    [string]$ActivationManifest,

    [Parameter(Mandatory = $true)]
    [string]$ImageDigest
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$failures = New-Object System.Collections.Generic.List[object]
$dotSourced = $MyInvocation.InvocationName -eq "."

function Add-Failure([string]$Code, [string]$Variable, [string]$Artifact, [string]$NextAction) {
    $failures.Add([pscustomobject]@{
        Code = $Code
        Variable = $Variable
        Artifact = $Artifact
        NextAction = $NextAction
    })
}

function Resolve-ExternalArtifact([string]$Value, [string]$Variable, [string]$Artifact, [string]$MissingCode, [string]$NextAction) {
    if ([string]::IsNullOrWhiteSpace($Value)) {
        Add-Failure $MissingCode $Variable $Artifact $NextAction
        return $null
    }

    try {
        if (-not (Test-Path -LiteralPath $Value -PathType Leaf)) {
            Add-Failure $MissingCode $Variable $Artifact $NextAction
            return $null
        }
        $resolved = (Resolve-Path -LiteralPath $Value -ErrorAction Stop).Path
        $repoPrefix = $repoRoot.TrimEnd('\') + '\'
        if ($resolved.Equals($repoRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
            $resolved.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            Add-Failure $MissingCode $Variable $Artifact "Obtain the separately reviewed artifact from approved external custody, then rerun this helper"
            return $null
        }
        return $resolved
    } catch {
        Add-Failure $MissingCode $Variable $Artifact $NextAction
        return $null
    }
}

$runtimePath = Resolve-ExternalArtifact `
    $ApprovedRuntimeModule `
    "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME" `
    "external approved Playwright runtime module" `
    "TB_PROVIDER_MODULE_MISSING" `
    "Obtain the reviewed runtime module from approved custody; do not install standalone Playwright or use a test fixture"
$manifestPath = Resolve-ExternalArtifact `
    $ActivationManifest `
    "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST" `
    "external Gate 4 activation manifest" `
    "TB_PROVIDER_MANIFEST_MISSING" `
    "Obtain the integrity-checked activation manifest and operator approval record from approved custody"

if ([string]::IsNullOrWhiteSpace($ImageDigest) -or $ImageDigest -notmatch '^sha256:[0-9a-fA-F]{64}$') {
    Add-Failure "TB_IMAGE_IDENTITY_INVALID" "SENTINEL_DNA_IMAGE_DIGEST" "reviewed staging image digest" "Use the immutable sha256 digest of the deployed staging image and reconcile it in the external activation manifest"
}

if ($failures.Count -gt 0) {
    Write-Output "STATUS=BLOCKED_WITH_REASON"
    foreach ($failure in $failures) {
        Write-Output "VARIABLE=$($failure.Variable)"
        Write-Output "ARTIFACT=$($failure.Artifact)"
        Write-Output "DIAGNOSTIC=$($failure.Code)"
        Write-Output "NEXT_ACTION=$($failure.NextAction)"
    }
    if (-not $dotSourced) { exit 1 }
    return
}

# This helper sets only non-secret Gate 4 configuration in the current
# PowerShell scope. Dot-source it when the variables must remain in the
# operator shell: . .\configure_gate4_provider_environment.ps1 ...
$env:SENTINEL_DNA_ENV = "staging"
$env:SENTINEL_DNA_IMAGE_DIGEST = $ImageDigest
$env:SENTINEL_DNA_TRUSTED_BROWSER_CLIENT = Join-Path $repoRoot "deployment\staging\scripts\trusted_browser_service\browser-client.mjs"
$env:SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT = Join-Path $repoRoot "deployment\staging\scripts\trusted_browser_service\providers\playwright-runtime-provider.mjs"
$env:SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME = $runtimePath
$env:SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST = $manifestPath

Write-Output "STATUS=PASS"
Write-Output "CHECK=PASS:Gate 4 provider facade and approved provider boundary configured"
