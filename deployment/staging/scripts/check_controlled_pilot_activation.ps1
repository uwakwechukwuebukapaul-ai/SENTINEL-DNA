[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

# This command never mutates the browser, runtime, or application. Normal mode
# writes one non-secret readiness report; -DryRun validates without that file.
$safeCodes = New-Object System.Collections.Generic.List[string]
$requiredVariables = @(
    "SENTINEL_DNA_ENV",
    "SENTINEL_DNA_IMAGE_DIGEST",
    "SENTINEL_DNA_TRUSTED_BROWSER_CLIENT",
    "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT",
    "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME",
    "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST",
    "SENTINEL_DNA_PILOT_ACCESS_REQUIRED",
    "SENTINEL_DNA_SECURE_COOKIES",
    "FLASK_DEBUG",
    "SENTINEL_DNA_TENANT_ISOLATION_ENABLED",
    "SENTINEL_DNA_AUDIT_LOGGING_ENABLED"
)
$providerVariables = @(
    "SENTINEL_DNA_TRUSTED_BROWSER_CLIENT",
    "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT",
    "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME"
)
$fileVariables = $providerVariables + "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST"

function Add-SafeCode([string]$Code) {
    if (-not $safeCodes.Contains($Code)) { $safeCodes.Add($Code) }
}

foreach ($name in $requiredVariables) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        if ($providerVariables -contains $name) { Add-SafeCode "TB_PROVIDER_NOT_CONFIGURED" }
        elseif ($name -eq "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST") { Add-SafeCode "TB_PROVIDER_MANIFEST_MISSING" }
        elseif ($name -eq "SENTINEL_DNA_IMAGE_DIGEST") { Add-SafeCode "TB_IMAGE_IDENTITY_INVALID" }
        else { Add-SafeCode "TB_SECURITY_CONTROL_MISSING" }
    }
}

$imageDigest = [Environment]::GetEnvironmentVariable("SENTINEL_DNA_IMAGE_DIGEST")
if (-not [string]::IsNullOrWhiteSpace($imageDigest) -and $imageDigest -notmatch '^sha256:[0-9a-fA-F]{64}$') {
    Add-SafeCode "TB_IMAGE_IDENTITY_INVALID"
}
if ([Environment]::GetEnvironmentVariable("SENTINEL_DNA_ENV") -ne "staging") {
    Add-SafeCode "TB_SECURITY_CONTROL_MISSING"
}

foreach ($name in $fileVariables) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if (-not [string]::IsNullOrWhiteSpace($value)) {
        try {
            if (-not (Test-Path -LiteralPath $value -PathType Leaf)) {
                if ($name -eq "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST") { Add-SafeCode "TB_PROVIDER_MANIFEST_MISSING" }
                else { Add-SafeCode "TB_PROVIDER_MODULE_MISSING" }
            }
            $normalized = $value.Replace("\", "/").ToLowerInvariant()
            if ($normalized.Contains("/tests/staging/") -or $normalized.Contains("trusted-playwright-adapter-stub")) {
                Add-SafeCode "TB_PROVIDER_MODULE_MISSING"
            }
        } catch {
            if ($name -eq "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST") { Add-SafeCode "TB_PROVIDER_MANIFEST_MISSING" }
            else { Add-SafeCode "TB_PROVIDER_MODULE_MISSING" }
        }
    }
}

$expectedValues = @{
    "SENTINEL_DNA_PILOT_ACCESS_REQUIRED" = "1"
    "SENTINEL_DNA_SECURE_COOKIES" = "1"
    "FLASK_DEBUG" = "0"
    "SENTINEL_DNA_TENANT_ISOLATION_ENABLED" = "1"
    "SENTINEL_DNA_AUDIT_LOGGING_ENABLED" = "1"
}
foreach ($entry in $expectedValues.GetEnumerator()) {
    if ([Environment]::GetEnvironmentVariable($entry.Key) -ne $entry.Value) {
        Add-SafeCode "TB_SECURITY_CONTROL_MISSING"
    }
}

# The Node checks are authoritative for manifest hashing, digest binding,
# browser contract, browserAuth, certified-origin reachability, and evidence
# custody. Suppress all non-machine-readable process diagnostics.
$reportScript = Join-Path $PSScriptRoot "generate_trusted_browser_readiness_report.mjs"
$readinessScript = Join-Path $PSScriptRoot "check_controlled_pilot_readiness.mjs"
if (-not (Test-Path -LiteralPath $reportScript -PathType Leaf) -or
    -not (Test-Path -LiteralPath $readinessScript -PathType Leaf)) {
    Add-SafeCode "TB_RUNTIME_UNAVAILABLE"
}

function Get-NodeJson([string]$ScriptPath, [string[]]$Arguments = @()) {
    try {
        $output = @(& node $ScriptPath @Arguments 2>$null)
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0 -and $output.Count -eq 0) { return $null }
        return (($output -join [Environment]::NewLine) | ConvertFrom-Json)
    } catch {
        return $null
    }
}

if ($safeCodes.Count -eq 0) {
    $scriptArguments = @()
    if (-not $DryRun) {
        $artifactDirectory = Join-Path $PSScriptRoot "../../../pilot-evidence"
        $artifactTimestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffZ")
        $artifactPath = Join-Path $artifactDirectory "controlled-pilot-readiness-report-$artifactTimestamp.json"
        $scriptArguments = @("--output", $artifactPath)
    }
    $report = Get-NodeJson $reportScript $scriptArguments
    $readiness = Get-NodeJson $readinessScript @()
    if ($null -eq $report -or $null -eq $readiness) {
        Add-SafeCode "TB_RUNTIME_UNAVAILABLE"
    } else {
        foreach ($check in @($report.checks)) {
            if ($check.status -ne "PASS") {
                switch ($check.name) {
                    "provider_configured" { Add-SafeCode "TB_PROVIDER_NOT_CONFIGURED" }
                    "runtime_reachable" { Add-SafeCode ([string]$check.reason) }
                    "browser_contract_valid" { Add-SafeCode ([string]$check.reason) }
                    "origin_reachable" { Add-SafeCode "TB_ORIGIN_UNREACHABLE" }
                    "browser_auth_available" { Add-SafeCode "TB_AUTH_CAPABILITY_MISSING" }
                    "evidence_directory_writable" { Add-SafeCode "TB_EVIDENCE_DIRECTORY_UNAVAILABLE" }
                    "activation_report_artifact" { Add-SafeCode "TB_EVIDENCE_DIRECTORY_UNAVAILABLE" }
                    "activation_manifest_valid" { Add-SafeCode ([string]$check.reason) }
                    default { Add-SafeCode "TB_RUNTIME_UNAVAILABLE" }
                }
            }
        }
        foreach ($check in @($readiness.checks)) {
            if ($check.status -ne "PASS") {
                switch ($check.name) {
                    "image_digest" { Add-SafeCode "TB_IMAGE_IDENTITY_INVALID" }
                    "staging_environment" { Add-SafeCode "TB_SECURITY_CONTROL_MISSING" }
                    "activation_manifest" { Add-SafeCode ([string]$check.reason) }
                    "provider_configured" { Add-SafeCode "TB_PROVIDER_NOT_CONFIGURED" }
                    "provider_verification" { Add-SafeCode ([string]$check.reason) }
                    "evidence_directory" { Add-SafeCode "TB_EVIDENCE_DIRECTORY_UNAVAILABLE" }
                    "activation_report_artifact" { Add-SafeCode "TB_EVIDENCE_DIRECTORY_UNAVAILABLE" }
                    "certified_origin" { Add-SafeCode "TB_ORIGIN_UNREACHABLE" }
                    default { Add-SafeCode "TB_SECURITY_CONTROL_MISSING" }
                }
            }
        }
    }
}

$safeCodes = @($safeCodes | Where-Object { $_ -match '^TB_[A-Z0-9_]+$' } | Sort-Object -Unique)
if ($DryRun -and -not $Json) { Write-Output "MODE=DRY_RUN" }
if ($safeCodes.Count -gt 0) {
    if ($Json) {
        @{ status = "BLOCKED_WITH_REASON"; codes = @($safeCodes) } | ConvertTo-Json -Compress
    } else {
        Write-Output "BLOCKED_WITH_REASON"
        foreach ($code in $safeCodes) { Write-Output "CODE=$code" }
    }
    exit 1
}

if ($Json) { @{ status = "READY_FOR_ANALYST_PILOT"; codes = @() } | ConvertTo-Json -Compress }
else { Write-Output "READY_FOR_ANALYST_PILOT" }
exit 0
