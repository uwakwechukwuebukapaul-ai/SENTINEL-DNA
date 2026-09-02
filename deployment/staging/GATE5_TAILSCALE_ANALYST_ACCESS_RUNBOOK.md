# Gate 5 Tailscale Private Analyst Access Runbook

## Scope and status

This is the selected private-access path for the first real Gate 5 analyst
login. It prepares one bounded, synthetic-data-only staging run. It does not
create an analyst, approve a run, create pilot evidence, or authorize
production access. Until the real workflow is completed and reviewed, status
remains `READY_FOR_ANALYST_PILOT`.

The path is:

```text
approved analyst device with Tailscale client
        -> deny-by-default tailnet grant/ACL (TCP 443 only)
        -> Tailscale Serve raw TCP forwarder
        -> 127.0.0.1:18443 on the staging host
        -> existing HTTPS edge and Sentinel DNA application
```

The browser URL is exactly `https://uwakwe-desktop.taile388cc.ts.net`. Tailscale
Serve accepts private tailnet TCP/443 and forwards the encrypted TLS stream to
the existing loopback-only staging edge at 127.0.0.1:18443. The
database, Redis, Docker, SSH, Tailscale SSH, shell/container, metrics,
management, repository, LAN, subnet routes, exit nodes, and production
surfaces are outside the route.

## Hard stops

Stop before analyst authentication for a missing Gate 4 PASS, missing backup or
restore approval, missing external approval, default-allow tailnet policy,
wildcard/broad CIDR/exit-node/subnet route, Funnel/public exposure, HTTPS or
TLS-terminated Serve, `https+insecure`, alternate origin, non-loopback Docker
publication, failed CA/SNI validation, internal-service reachability, or any
credential/session value in logs or evidence.

Tailscale's current policy model supports grants and legacy ACLs; use one
explicit, least-privilege policy for the run. An absent policy can leave a
tailnet default-allow, so policy presence and scope are part of this gate.

## 1. Prepare external Tailscale state

1. Enroll the staging host and exactly one approved analyst device in the
   externally managed tailnet. Require the approved identity provider/MFA and
   record the device/node references outside Git.
2. Copy the secret-free
   [`tailscale/tailnet-policy.example.hujson`](tailscale/tailnet-policy.example.hujson)
   outside the repository. Replace the placeholder with the approved analyst
   identity only; keep the `grants` scope at the staging tag and TCP `443`.
3. Apply the policy through the approved Tailscale admin/custody process. Do
   not use `*`, `autogroup:member`, broad CIDRs, `autogroup:internet`, subnet
   routes, exit nodes, or Tailscale SSH for this run.
4. Configure raw TCP forwarding on the staging node:

   ```powershell
   tailscale serve --bg --tcp=443 tcp://127.0.0.1:18443
   ```

   This forwards the analyst's TLS bytes without terminating TLS. Do not use
   `--https`, `--tls-terminated-tcp`, `https+insecure`, or `tailscale funnel`.
   Run it under the approved host service mechanism and retain its status
   externally.
5. Use the tailnet's MagicDNS name
   `uwakwe-desktop.taile388cc.ts.net`. Verify it resolves only to
   `100.121.164.69` on the staging node and the enrolled device. Do not create
   a public A/AAAA/CNAME record or point the name at a public proxy.

## 2. Read-only preflight

Run on the approved staging host/operator device, then repeat the origin and
surface checks from the enrolled analyst device:

```powershell
.\deployment\staging\scripts\validate_tailscale_private_access.ps1 `
  -TailnetPolicyFile 'C:\approved\tailscale\gate5-policy.hujson' `
  -AnalystSelector 'group:sentinel-dna-gate5-analysts' `
  -DestinationSelector 'tag:sentinel-dna-staging' `
  -CaFile 'C:\approved\sentinel-dna-tls\staging-ca.crt' `
  -ComposeEnvFile 'C:\approved\sentinel-dna-secrets\staging.env'
```

The helper checks external custody, the live Tailscale node and raw Serve
forwarder, exact policy scope, loopback-only Docker publication, private DNS,
TCP reachability, and CA/SNI-verified `/health` and `/ready`. A zero exit code
is only a boundary preflight; it is not analyst authentication or pilot
evidence.

From the analyst device, separately verify that PostgreSQL, Redis, SSH,
Docker, Tailscale SSH, shell/container, metrics, management, repository, LAN,
subnet, exit-node, and production destinations are denied or unroutable. Use
externally supplied destination values; do not add them to this repository.

## 3. Open the Gate 5 run

1. Confirm Gate 4 returns `READY_FOR_ANALYST_PILOT` with 13/13 checks PASS.
2. Confirm fresh staging backup and isolated-restore evidence and the external
   human approval for one synthetic tenant, one analyst, one scenario set,
   expiry, operator, reviewer, and rollback owner.
3. Create a unique external run ID and append-only access record using
   `GATE5_ANALYST_ACCESS_EVIDENCE.schema.json`, with
   `evidence_class: remote_access_preflight`,
   `access_method: tailscale_private_overlay`, and status `NOT_EXECUTED`.
4. Record only opaque Tailscale policy/node/device/forwarding/custody
   references. Never record auth keys, recovery keys, passwords, cookies, CSRF
   values, bearer tokens, or session identifiers.

## 4. First analyst login and closeout

Follow [`GATE5_ANALYST_ONBOARDING_CHECKLIST.md`](GATE5_ANALYST_ONBOARDING_CHECKLIST.md)
for manager authentication, protected provisioning, analyst activation,
server-derived role/tenant verification, RBAC and tenant-isolation checks,
audit/provenance capture, and revocation. The first login must use exactly
`https://uwakwe-desktop.taile388cc.ts.net`; a Tailscale connection alone is not
Sentinel DNA authentication evidence.

After the approved workflow, revoke authorization, deactivate the analyst,
invalidate sessions, verify reads/writes fail closed, disable or narrow the
Tailscale grant and Serve listener, and seal the external evidence. Use the
authenticated pilot class only after all direct observations, hashes, custody,
and human review are complete. Otherwise retain `NOT_MEASURED` or
`BLOCKED_WITH_REASON`.

## Official references

- [Tailscale grants](https://tailscale.com/docs/features/access-control/grants)
- [Tailscale policy syntax](https://tailscale.com/docs/reference/syntax/policy-file)
- [Tailscale Serve TCP forwarding](https://tailscale.com/docs/reference/tailscale-cli/serve)
