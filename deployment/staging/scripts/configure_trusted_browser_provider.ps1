[CmdletBinding()]
param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$requiredVariables = @(
    "SENTINEL_DNA_ENV",
    "SENTINEL_DNA_IMAGE_DIGEST",
    "SENTINEL_DNA_TRUSTED_BROWSER_CLIENT",
    "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT",
    "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME",
    "SENTINEL_DNA_APPROVED_RUNTIME_DIGEST",
    "SENTINEL_DNA_BROWSER_AUTH_BRIDGE",
    "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST",
    "SENTINEL_DNA_PILOT_ACCESS_REQUIRED",
    "SENTINEL_DNA_SECURE_COOKIES",
    "FLASK_DEBUG",
    "SENTINEL_DNA_TENANT_ISOLATION_ENABLED",
    "SENTINEL_DNA_AUDIT_LOGGING_ENABLED"
)

$fileVariables = @(
    "SENTINEL_DNA_TRUSTED_BROWSER_CLIENT",
    "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT",
    "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME",
    "SENTINEL_DNA_BROWSER_AUTH_BRIDGE",
    "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST"
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$expectedProviderFiles = @{
    "SENTINEL_DNA_TRUSTED_BROWSER_CLIENT" = (Join-Path $repoRoot "deployment\staging\scripts\trusted_browser_service\browser-client.mjs")
    "SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT" = (Join-Path $repoRoot "deployment\staging\scripts\trusted_browser_service\providers\playwright-runtime-provider.mjs")
}

$failures = New-Object System.Collections.Generic.List[string]

foreach ($name in $requiredVariables) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        $failures.Add("$name is missing")
    }
}

$imageDigest = [Environment]::GetEnvironmentVariable("SENTINEL_DNA_IMAGE_DIGEST")
if (-not [string]::IsNullOrWhiteSpace($imageDigest) -and $imageDigest -notmatch '^sha256:[0-9a-fA-F]{64}$') {
    $failures.Add("SENTINEL_DNA_IMAGE_DIGEST is invalid")
}
$runtimeDigest = [Environment]::GetEnvironmentVariable("SENTINEL_DNA_APPROVED_RUNTIME_DIGEST")
if (-not [string]::IsNullOrWhiteSpace($runtimeDigest) -and $runtimeDigest -notmatch '^sha256:[0-9a-fA-F]{64}$') {
    $failures.Add("SENTINEL_DNA_APPROVED_RUNTIME_DIGEST is invalid")
}

if ([Environment]::GetEnvironmentVariable("SENTINEL_DNA_ENV") -ne "staging") {
    $failures.Add("SENTINEL_DNA_ENV must be staging")
}

foreach ($name in $fileVariables) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if (-not [string]::IsNullOrWhiteSpace($value)) {
        try {
            if (-not (Test-Path -LiteralPath $value -PathType Leaf)) {
                $failures.Add("$name does not reference an existing file")
            }
            $normalized = $value.Replace("\", "/").ToLowerInvariant()
            if ($normalized.Contains("/tests/staging/") -or $normalized.Contains("trusted-playwright-adapter-stub")) {
                $failures.Add("$name references a test-only provider")
            }
        } catch {
            $failures.Add("$name does not reference a readable local file")
        }
    }
}

foreach ($entry in $expectedProviderFiles.GetEnumerator()) {
    $configured = [Environment]::GetEnvironmentVariable($entry.Key)
    if (-not [string]::IsNullOrWhiteSpace($configured)) {
        try {
            $actual = (Resolve-Path -LiteralPath $configured -ErrorAction Stop).Path
            $expected = (Resolve-Path -LiteralPath $entry.Value -ErrorAction Stop).Path
            if ($actual -ne $expected) {
                $failures.Add("$($entry.Key) does not resolve to the reviewed repository module")
            }
        } catch {
            $failures.Add("$($entry.Key) does not resolve to the reviewed repository module")
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
        $failures.Add("$($entry.Key) must be $($entry.Value)")
    }
}

if ($DryRun) {
    Write-Output "MODE=DRY_RUN"
}

if ($failures.Count -gt 0) {
    Write-Output "STATUS=BLOCKED_WITH_REASON"
    foreach ($failure in $failures) {
        Write-Output "CHECK=FAIL:$failure"
    }
    exit 1
}

Write-Output "STATUS=PASS"
Write-Output "CHECK=PASS:provider configuration and security assertions"
exit 0
