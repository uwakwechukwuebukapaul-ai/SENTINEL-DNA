# Gate 5 Cloudflare Private Analyst Access Runbook

> **PAUSED:** Cloudflare Zero Trust is paused for the current Gate 5 run. This
> runbook is retained as a future reference only; do not configure or use it
> for the first analyst login. Use the Tailscale path instead:
> [`GATE5_TAILSCALE_ANALYST_ACCESS_RUNBOOK.md`](GATE5_TAILSCALE_ANALYST_ACCESS_RUNBOOK.md).

## Scope and decision

This runbook prepares one bounded, non-production analyst access path. It does
not change Sentinel DNA application architecture, Docker topology, or
production deployment, and it does not create pilot evidence. The status stays
`READY_FOR_ANALYST_PILOT` until one real controlled analyst run is completed,
externally captured, validated, and human-reviewed.

The selected pattern is:

```text
approved analyst device with Cloudflare One Client
        -> Cloudflare private-hostname route + private Access policy
        -> outbound-only cloudflared connector on the staging host
        -> existing HTTPS edge at 127.0.0.1:18443
        -> existing Sentinel DNA application
```

The browser URL remains exactly `https://sentinel-dna-staging:18443`.
PostgreSQL, Redis, Docker, SSH, shell/container, metrics, management,
repository, and production surfaces are outside the route.

## Preconditions and hard stops

Before changing Cloudflare, the operator must have:

- Gate 4 `READY_FOR_ANALYST_PILOT` with all 13 checks PASS;
- the reviewed commit `5ed93bed85b65bbf75276eeb2aeb8b29da185c44` reconciled with
  external runtime, image, browser, TLS, and custody records;
- fresh staging backup and isolated-restore approval/evidence;
- one approved analyst, one synthetic tenant, one scenario set, a short UTC
  expiry, and named security/rollback owners;
- a non-production CA bundle trusted by the analyst device and the connector;
- all populated tunnel configuration, credentials, CA/private keys, and
  Cloudflare policy records held outside Git.

Stop immediately for a public hostname/DNS record, wildcard route, broad CIDR,
`noTLSVerify`, alternate origin, edge rebinding, internal-service exposure,
missing approval, or an unmeasured control. Do not solve a connectivity failure
by changing Sentinel DNA's Host/origin checks, cookie scope, CSRF behavior,
RBAC, tenant handling, or audit behavior.

## 1. Prepare the connector configuration

1. Create or select a dedicated non-production named Tunnel in Cloudflare.
2. Copy [`cloudflare/tunnel-config.yml.example`](cloudflare/tunnel-config.yml.example)
   to an external path. Replace the tunnel UUID and credentials-file path only.
3. Keep `warp-routing.enabled: true`. Do not add an `ingress` section, public
   hostname, DNS route, quick tunnel, token, or service mapping.
4. Run `cloudflared` on the staging host (or an explicitly approved connector
   that can reach the existing loopback edge). The host-level path must reach
   `https://sentinel-dna-staging:18443` without changing Docker's
   `127.0.0.1:18443->443/tcp` publication. If that cannot be achieved without
   broadening the edge listener, stop and obtain a separately reviewed network
   design.
5. Install/start the connector using the approved host service mechanism. Do
   not put its credential value in a command line, shell history, log, ticket,
   screenshot, or evidence record.

## 2. Configure the Cloudflare private boundary

In the Cloudflare Zero Trust dashboard, or through the approved infrastructure
configuration process:

1. Add exactly one private-hostname route for `sentinel-dna-staging`; use port
   `18443` and no wildcard. The route must resolve through the connector to the
   existing staging edge only.
2. Create/select a self-hosted **private** Access application for
   `sentinel-dna-staging:18443`. Do not select a public-hostname application.
3. Add an explicit Allow policy for the single approved analyst identity and,
   only if required by the run, the named operator identity. Keep the default
   deny posture; do not use Everyone, all-valid-emails, unauthenticated,
   service-token-only, or Bypass rules.
4. Require the approved identity provider, MFA, enrolled Cloudflare One Client
   device, and any approved posture rule. Set a short session duration and the
   external UTC expiry for this run.
5. Keep Cloudflare access logs separate from Sentinel DNA audit evidence. A
   Cloudflare log proves perimeter entry only; it does not prove application
   authentication, RBAC, tenant isolation, provenance, or revocation.
6. Configure private DNS/Gateway and split-tunnel behavior only for the exact
   private hostname route. Do not advertise the staging LAN, Docker network,
   PostgreSQL, Redis, production network, or a broad RFC1918 range.

Cloudflare's private-network mode requires the Cloudflare One Client (or an
approved private-network on-ramp) on the analyst device. Clientless Browser
Isolation is not accepted for this non-default HTTPS port unless a separate
compatibility review approves it.

## 3. Validate before analyst authentication

Run the repository helper from the approved operator host with populated paths
that are outside the repository:

```powershell
.\deployment\staging\scripts\validate_cloudflare_private_access.ps1 `
  -TunnelConfig 'C:\approved\cloudflared\sentinel-dna-staging.yml' `
  -CaFile 'C:\approved\sentinel-dna-tls\staging-ca.crt' `
  -ComposeEnvFile 'C:\approved\sentinel-dna-secrets\staging.env'
```

The helper is read-only. It checks the private-only tunnel shape, external
credential/configuration custody, loopback edge publication, connector state,
DNS reachability, and CA/SNI-verified `/health` and `/ready` responses. A zero
exit code is only a boundary preflight; it is not analyst pilot evidence.

If a manual check is needed, use the same exact origin and CA:

```powershell
cloudflared --config 'C:\approved\cloudflared\sentinel-dna-staging.yml' tunnel info __TUNNEL_UUID__
docker compose --env-file 'C:\approved\sentinel-dna-secrets\staging.env' `
  --file .\deployment\staging\docker-compose.yml port edge 443
Resolve-DnsName sentinel-dna-staging
Test-NetConnection sentinel-dna-staging -Port 18443
curl.exe --fail --silent --show-error --cacert 'C:\approved\sentinel-dna-tls\staging-ca.crt' `
  --output NUL --write-out "%{http_code}" https://sentinel-dna-staging:18443/health
curl.exe --fail --silent --show-error --cacert 'C:\approved\sentinel-dna-tls\staging-ca.crt' `
  --output NUL --write-out "%{http_code}" https://sentinel-dna-staging:18443/ready
```

Require the edge output to show only `127.0.0.1:18443` and both health codes
to be `200`. Curl's CA validation and URL hostname provide the TLS certificate
and SNI check; never use `-k`, an alternate hostname, or an IP URL.

From the enrolled analyst device, repeat the DNS, port, and CA-verified HTTPS
checks. Separately verify that the staging host's database, Redis, SSH, Docker,
shell, metrics, management, and production destinations are denied or
unroutable. Use only externally supplied destination values for those checks;
do not add them to this repository.

## 4. Onboard the approved analyst

Use [`GATE5_ANALYST_ONBOARDING_CHECKLIST.md`](GATE5_ANALYST_ONBOARDING_CHECKLIST.md)
as the authoritative checklist.

1. Create a unique external run ID and an append-only preflight record with
   class `remote_access_preflight` and status `NOT_EXECUTED`.
2. Have the manager authenticate through the existing protected browser-auth
   flow and directly verify manager role, secure cookies, active session, and
   missing-CSRF denial before any protected write.
3. If approved, provision only one synthetic tenant and one analyst through
   the existing protected workflow. The operator must not handle or record the
   analyst password, activation value, cookie, CSRF value, bearer token, or
   session identifier.
4. Have the analyst use the enrolled device and open exactly
   `https://sentinel-dna-staging:18443`. Verify the server-derived `analyst`
   role, tenant scope, bounded authorization expiry, and analyst workspace.
5. Do not treat Cloudflare login or a successful health check as Sentinel DNA
   authentication evidence.

## 5. Controlled checks and closeout

Only after the real analyst login, execute the already approved synthetic,
non-destructive workflow. Directly observe RBAC denials, CSRF enforcement,
foreign-tenant denial/no leakage, audit/provenance references, advisory-only AI
handling, and post-revocation fail-closed behavior. Mark anything not observed
as `NOT_MEASURED`; do not create or promote fake evidence.

Then revoke the Sentinel DNA authorization, deactivate the analyst, invalidate
sessions, verify subsequent reads/writes fail closed, and disable or narrow the
Cloudflare policy/route. Seal the real record in external custody and run the
focused validators plus the full validator listed in the existing Gate 5
runbooks. A passing access preflight alone cannot advance Gate 5.

## Rollback

For unexpected access, TLS/origin drift, cross-tenant leakage, internal-service
reachability, audit gaps, credential exposure, or provider drift:

1. stop analyst activity;
2. disable the analyst Allow policy and private route/Cloudflare device access;
3. revoke Sentinel DNA authorization, deactivate the analyst, invalidate
   sessions, and verify denial;
4. preserve only opaque references and hashes in external custody; and
5. obtain fresh approval and a new run ID before restarting.

Do not alter application code or the Docker publication as a rollback measure.
