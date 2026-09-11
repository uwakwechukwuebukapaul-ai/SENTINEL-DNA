[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$TailnetPolicyFile,
    [Parameter(Mandatory = $true)] [string]$AnalystSelector,
    [Parameter(Mandatory = $true)] [string]$DestinationSelector,
    [Parameter(Mandatory = $true)] [string]$CaFile,
    [Parameter(Mandatory = $true)] [string]$ComposeEnvFile,
    [string]$ComposeFile,
    [string]$OriginHost = 'uwakwe-desktop.taile388cc.ts.net',
    [int]$OriginPort = 443,
    [string]$ExpectedNodeIPv4 = '100.121.164.69',
    [string]$ApprovedAnalystIPv4 = '100.99.42.93',
    [string]$FirewallRuleName = 'Sentinel DNA Gate5 Tailscale HTTPS',
    [string]$Tailscale = 'tailscale',
    [string]$Docker = 'docker'
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($ComposeFile)) { $ComposeFile = Join-Path $PSScriptRoot '..\docker-compose.yml' }

function Stop-Validation([string]$Message) { [Console]::Error.WriteLine("BLOCKED_WITH_REASON: $Message"); exit 2 }
function Resolve-ExistingFile([string]$Path, [string]$Label, [switch]$RequireAbsolute) {
    if ($RequireAbsolute -and -not [IO.Path]::IsPathRooted($Path)) { Stop-Validation "$Label must be an absolute external path" }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { Stop-Validation "$Label is missing" }
    return (Resolve-Path -LiteralPath $Path).Path
}
function Assert-ExternalPath([string]$Path, [string]$Label, [string]$RepoRoot) {
    if (-not [IO.Path]::IsPathRooted($Path)) { Stop-Validation "$Label must be an absolute external path" }
    $normalizedPath = [IO.Path]::GetFullPath($Path).TrimEnd([IO.Path]::DirectorySeparatorChar)
    $normalizedRoot = [IO.Path]::GetFullPath($RepoRoot).TrimEnd([IO.Path]::DirectorySeparatorChar)
    if ($normalizedPath.Equals($normalizedRoot, [StringComparison]::OrdinalIgnoreCase) -or $normalizedPath.StartsWith($normalizedRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { Stop-Validation "$Label must be outside the repository" }
}
function Invoke-Checked([string]$FilePath, [string[]]$Arguments, [string]$Label) {
    $output = & $FilePath @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { Stop-Validation "$Label failed" }
    return ($output -join "`n")
}
function In-TailscaleRange([System.Net.IPAddress]$Address) {
    if ($Address.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork) {
        $bytes = $Address.GetAddressBytes(); return ($bytes[0] -eq 100 -and $bytes[1] -ge 64 -and $bytes[1] -le 127)
    }
    return $Address.ToString().ToLowerInvariant().StartsWith('fd7a:115c:a1e0:')
}
function Get-IPv4([string]$Value, [string]$Label) {
    try { $address = [System.Net.IPAddress]::Parse($Value); if ($address.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) { Stop-Validation "$Label is not an IPv4 address" }; return $address.ToString() } catch { Stop-Validation "$Label is not a valid IP address" }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$policyPath = Resolve-ExistingFile $TailnetPolicyFile 'Tailnet policy' -RequireAbsolute
$caPath = Resolve-ExistingFile $CaFile 'CA bundle' -RequireAbsolute
$composeEnvPath = Resolve-ExistingFile $ComposeEnvFile 'Compose environment file' -RequireAbsolute
$composePath = Resolve-ExistingFile $ComposeFile 'Compose file'
Assert-ExternalPath $policyPath 'Tailnet policy' $repoRoot
Assert-ExternalPath $caPath 'CA bundle' $repoRoot
Assert-ExternalPath $composeEnvPath 'Compose environment file' $repoRoot

$ExpectedNodeIPv4 = Get-IPv4 $ExpectedNodeIPv4 'expected staging-node address'
$ApprovedAnalystIPv4 = Get-IPv4 $ApprovedAnalystIPv4 'approved analyst address'
if ($OriginHost -cne 'uwakwe-desktop.taile388cc.ts.net') { Stop-Validation 'the certified Gate 5 hostname is not being validated' }
if ($OriginPort -ne 443) { Stop-Validation 'the certified Gate 5 endpoint must use HTTPS TCP 443' }
if ($AnalystSelector -match '[*\r\n]' -or $DestinationSelector -match '[*\r\n]') { Stop-Validation 'wildcard or multiline selector is not allowed' }
if (-not (Get-Command $Tailscale -ErrorAction SilentlyContinue)) { Stop-Validation 'tailscale is not installed or is not on PATH' }
if (-not (Get-Command $Docker -ErrorAction SilentlyContinue)) { Stop-Validation 'docker is not installed or is not on PATH' }

$policyText = (Get-Content -LiteralPath $policyPath -Raw) -replace '(?m)//.*$', '' -replace '(?m)#.*$', ''
if ($policyText -match '__[A-Z0-9_]+__|REPLACE_WITH|<[^>]+>') { Stop-Validation 'tailnet policy still contains a placeholder' }
if ($policyText -notmatch '"(?:grants|acls)"\s*:') { Stop-Validation 'tailnet policy has no explicit grants or ACLs; default-allow is not accepted' }
if ($policyText -notmatch [regex]::Escape($AnalystSelector)) { Stop-Validation 'approved analyst selector is absent from the policy' }
if ($policyText -notmatch [regex]::Escape($DestinationSelector)) { Stop-Validation 'staging destination selector is absent from the policy' }
if ($policyText -notmatch '(?i)tcp\s*:\s*443') { Stop-Validation 'policy does not explicitly grant TCP 443' }
if ($policyText -match '(?i)tcp\s*:\s*18443|:\s*18443|\*|autogroup:(?!admin\b)[A-Za-z-]+|(?:\b\d{1,3}\.){3}\d{1,3}/\d{1,2}|(?:[0-9a-f]{0,4}:){2,}[0-9a-f:]+/\d{1,3}|"?via"?\s*:|"?ssh"?\s*:|"?autoApprovers"?\s*:') { Stop-Validation 'policy contains a broad source, destination, route, or non-certified port' }

$status = Invoke-Checked $Tailscale @('status', '--json') 'Tailscale status'
try { $statusObject = $status | ConvertFrom-Json } catch { Stop-Validation 'Tailscale status is not valid JSON' }
if ($statusObject.BackendState -ne 'Running') { Stop-Validation 'Tailscale node is not running' }
if (-not $statusObject.Self -or @($statusObject.Self.TailscaleIPs).Count -eq 0) { Stop-Validation 'Tailscale node has no assigned Tailscale address' }
$selfAddresses = @($statusObject.Self.TailscaleIPs | ForEach-Object { try { [System.Net.IPAddress]::Parse($_) } catch { Stop-Validation 'Tailscale node reported an invalid Tailscale address' } })
if (-not ($selfAddresses | Where-Object { In-TailscaleRange $_ })) { Stop-Validation 'Tailscale node has no address in the Tailscale range' }
if (-not ($selfAddresses | Where-Object { $_.ToString() -eq $ExpectedNodeIPv4 })) { Stop-Validation 'Tailscale node identity does not contain the expected staging address' }
$selfDnsName = ([string]$statusObject.Self.DNSName).TrimEnd('.')
if ($selfDnsName -cne $OriginHost) { Stop-Validation 'Tailscale node MagicDNS identity does not match the certified hostname' }
$analystPeer = @($statusObject.Peer.PSObject.Properties | ForEach-Object { $_.Value } | Where-Object { $_.Online -eq $true -and @($_.TailscaleIPs) -contains $ApprovedAnalystIPv4 })
if ($analystPeer.Count -ne 1) { Stop-Validation 'the approved analyst peer is not uniquely present and online in Tailscale status' }
if ([string]::IsNullOrWhiteSpace([string]$analystPeer[0].HostName)) { Stop-Validation 'the approved analyst peer has no node identity' }

$serveStatus = Invoke-Checked $Tailscale @('serve', 'status', '--json') 'Tailscale Serve status'
try { $null = $serveStatus | ConvertFrom-Json } catch { Stop-Validation 'Tailscale Serve status is not valid JSON' }
if ($serveStatus -match '(?i)funnel|https\+insecure|tls-terminated-tcp|0\.0\.0\.0|"HTTPS"') { Stop-Validation 'Serve status contains Funnel, TLS termination, insecure forwarding, or broad binding' }
if ($serveStatus -notmatch '(?s)"443"\s*:.*tcp://127\.0\.0\.1:18443') { Stop-Validation 'raw TCP Serve must forward tailnet TCP/443 to 127.0.0.1:18443' }

$composeConfigJson = Invoke-Checked $Docker @('compose', '--env-file', $composeEnvPath, '--file', $composePath, 'config', '--format', 'json') 'Docker Compose configuration check'
try { $composeConfig = $composeConfigJson | ConvertFrom-Json } catch { Stop-Validation 'Docker Compose did not return valid JSON configuration' }
$edgeService = $composeConfig.services.edge
if (-not $edgeService) { Stop-Validation 'authoritative Compose file has no edge service' }
$edgePorts = @($edgeService.ports)
if ($edgePorts.Count -ne 1) { Stop-Validation 'edge must publish exactly one port' }
$edgePortText = ($edgePorts | ConvertTo-Json -Compress)
if ($edgePortText -notmatch '"target"\s*:\s*443' -or $edgePortText -notmatch '"published"\s*:\s*18443' -or $edgePortText -notmatch '"host_ip"\s*:\s*"127\.0\.0\.1"') { Stop-Validation 'edge publication is not exactly 127.0.0.1:18443 to container port 443' }
foreach ($serviceProperty in @($composeConfig.services.PSObject.Properties)) { if ($serviceProperty.Name -ne 'edge' -and @($serviceProperty.Value.ports).Count -gt 0) { Stop-Validation "service $($serviceProperty.Name) has an unnecessary published port" } }

$netstat = Invoke-Checked 'netstat.exe' @('-ano', '-p', 'tcp') 'host listener inspection'
foreach ($line in ($netstat -split "`r?`n")) {
    if ($line -match '^\s*TCP\s+(\S+):(80|443)\s+\S+\s+LISTENING\s+') {
        if ($Matches[1] -in @('0.0.0.0', '::', '[::]', '*')) { Stop-Validation "host has a public/wildcard TCP $($Matches[2]) listener" }
    }
}

$firewallRule = Invoke-Checked 'netsh.exe' @('advfirewall', 'firewall', 'show', 'rule', "name=$FirewallRuleName", 'dir=in') 'Gate 5 firewall rule inspection'
if ($firewallRule -notmatch '(?im)^\s*Enabled:\s+Yes' -or $firewallRule -notmatch '(?im)^\s*Action:\s+Allow' -or $firewallRule -notmatch '(?im)^\s*Protocol:\s+TCP' -or $firewallRule -notmatch "(?im)^\s*LocalIP:\s+$([regex]::Escape($ExpectedNodeIPv4))\s*$" -or $firewallRule -notmatch "(?im)^\s*RemoteIP:\s+$([regex]::Escape($ApprovedAnalystIPv4))\s*$" -or $firewallRule -notmatch '(?im)^\s*LocalPort:\s+443\s*$') { Stop-Validation 'the exact approved-analyst TCP/443 firewall rule is missing or broader than required' }
$allFirewallRules = Invoke-Checked 'netsh.exe' @('advfirewall', 'firewall', 'show', 'rule', 'name=all', 'dir=in') 'inbound firewall inspection'
$broadTailscaleRules = [regex]::Matches($allFirewallRules, '(?ms)^\s*Rule Name:\s+Tailscale-In\s*$.*?(?=^\s*Rule Name:|\z)')
foreach ($ruleMatch in $broadTailscaleRules) { $rule = $ruleMatch.Value; if ($rule -match '(?im)^\s*Enabled:\s+Yes' -and $rule -match '(?im)^\s*Action:\s+Allow' -and $rule -match '(?im)^\s*RemoteIP:\s+Any' -and $rule -match '(?im)^\s*Protocol:\s+Any') { Stop-Validation 'broad enabled Tailscale-In firewall rule remains active' } }

try {
    $dns = @(Resolve-DnsName $OriginHost -Type A -ErrorAction Stop | Where-Object { $_.IPAddress })
    $addresses = @($dns | ForEach-Object { [System.Net.IPAddress]::Parse($_.IPAddress) })
    if ($addresses.Count -ne 1 -or $addresses[0].ToString() -ne $ExpectedNodeIPv4) { Stop-Validation 'MagicDNS does not resolve exactly to the intended staging node' }
    if (-not ($selfAddresses | Where-Object { $_.Equals($addresses[0]) })) { Stop-Validation 'MagicDNS address is not assigned to the staging Tailscale node' }
    $unexpected = @(Resolve-DnsName $OriginHost -ErrorAction Stop | Where-Object { $_.IPAddress -and $_.IPAddress -ne $ExpectedNodeIPv4 })
    if ($unexpected.Count -gt 0) { Stop-Validation 'MagicDNS returned an unexpected address' }
} catch { Stop-Validation 'certified MagicDNS hostname does not resolve to the staging Tailscale address' }
if (-not (Test-NetConnection -ComputerName $OriginHost -Port 443 -InformationLevel Quiet)) { Stop-Validation 'private HTTPS origin is unreachable' }

$originBase = "https://$OriginHost"
foreach ($path in @('/health', '/ready')) {
    $url = "$originBase$path"
    $curlResult = (& curl.exe '--fail' '--silent' '--show-error' '--max-time' '15' '--cacert' $caPath '--output' 'NUL' '--write-out' '%{http_code} %{url_effective}' $url 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $curlResult -notmatch "^200 $([regex]::Escape($url))$") { Stop-Validation "CA/SNI-verified $path check failed" }
}

Write-Output 'PASS: Tailscale node and approved analyst peer are running'
Write-Output 'PASS: explicit least-privilege tailnet policy grants only TCP/443'
Write-Output 'PASS: raw TCP Tailscale Serve forwards to the loopback HTTPS edge'
Write-Output 'PASS: external policy, CA, and Compose custody'
Write-Output 'PASS: staging edge has exactly one loopback publication and no other published services'
Write-Output 'PASS: no wildcard host listener or broad Tailscale-In firewall rule'
Write-Output 'PASS: exact analyst-to-staging TCP/443 firewall rule'
Write-Output 'PASS: MagicDNS resolves exactly to the intended staging Tailscale address'
Write-Output 'PASS: HTTPS CA/SNI validation for /health and /ready'
Write-Output 'Boundary preflight passed; no analyst pilot evidence was created.'
