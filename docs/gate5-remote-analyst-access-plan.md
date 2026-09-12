# Gate 5 Remote Analyst Access Plan

## Decision

Sentinel DNA remains at `READY_FOR_ANALYST_PILOT`. This plan prepares remote
access to the existing non-production staging deployment; it does not claim
pilot completion or production readiness.

The selected access pattern is a narrowly scoped Tailscale private overlay.
It must use a deny-by-default tailnet grant/ACL, one approved analyst device,
one tagged staging node, TCP `443` only, short-lived access, and explicit
device/user approval. Tailscale Serve must use raw TCP forwarding to the
existing loopback edge; no subnet router, exit node, Tailscale SSH, or public
Funnel route is in scope. The overlay may reach only the staging browser
surface. It must not expose SSH, Docker, PostgreSQL, Redis, management,
metrics, shell, or repository access.

The operator procedure is
[`GATE5_TAILSCALE_ANALYST_ACCESS_RUNBOOK.md`](../deployment/staging/GATE5_TAILSCALE_ANALYST_ACCESS_RUNBOOK.md).

## Current architecture boundary

The reviewed staging deployment is:

```text
remote approved analyst
        │ private access overlay only
        ▼
staging host / private connector
        │ exact certified origin: https://uwakwe-desktop.taile388cc.ts.net
        │ edge publication: 127.0.0.1:18443 -> 443/tcp
        ▼
Docker edge ── staging_edge ── app ── staging_internal ── PostgreSQL
                                      └────────────────── Redis
```

The application, investigation engine, database schema, authentication logic,
tenant isolation logic, audit logic, Docker Compose contract, and trusted
browser origin checks are now aligned to the MagicDNS endpoint above. Remote
access remains an external network and custody concern only.

## Non-negotiable invariants

- The browser-visible origin remains exactly
  `https://uwakwe-desktop.taile388cc.ts.net`.
- TLS verification uses the approved CA and the
  `uwakwe-desktop.taile388cc.ts.net`
  certificate/SNI. No `-k`, TLS-ignore, alternate hostname, port, or origin
  exception is allowed.
- The edge remains loopback-only. A remote access connector may forward to the
  existing staging surface only through a reviewed host-level path.
- The remote policy is identity-restricted, time-bounded, and default-deny.
- The analyst receives no production route, customer data, database access,
  shell, container access, or management capability.
- Existing CSRF, RBAC, tenant, audit, provenance, human-decision, and
  revocation controls remain authoritative.
- Credentials, cookies, session material, Tailscale auth keys, private keys, and
  database backups remain outside Git and outside evidence records.

## Access-option assessment

| Option | Assessment | Decision |
| --- | --- | --- |
| Tailscale private overlay | Selected minimal-change path. Requires explicit grant/ACL scope, enrolled device, raw TCP Serve forwarding, exact-origin TLS validation, and host/node lifecycle control. | Selected |
| Narrowly routed WireGuard private overlay | Requires separate approval and careful route/ACL/peer lifecycle management because the edge is loopback-bound. | Not selected |
| Temporary VPS | Adds a second deployment, new custody, new TLS/runtime identity, and data-transfer risk. | Last resort only |
| PythonAnywhere | Does not preserve the Docker Compose, internal service, image custody, and exact-origin contract. | Reject |

## Analyst onboarding workflow

1. Security/release owner approves the remote access method, analyst identity,
   scope, expiry, device posture, and rollback owner.
2. Operator verifies Gate 4 readiness and reconciles runtime, image, bridge,
   manifest, TLS, and external custody identities.
3. Operator completes fresh staging backup and isolated restore evidence before
   any pilot mutation.
4. Manager authenticates through the approved browser-auth path. No credentials
   are placed in commands, logs, or evidence.
5. Manager provisions exactly one synthetic tenant and one analyst through the
   protected application workflow, if authorized for the run.
6. Analyst authenticates through the approved channel and confirms the
   server-derived analyst role and tenant scope.
7. Operator records only opaque identity, authorization, audit, provenance,
   and custody references.
8. Analyst performs one approved non-destructive synthetic investigation.
9. Operator performs the RBAC denial matrix, cross-tenant denial, audit and
   provenance review, and session-revocation test.
10. Operator revokes authorization, deactivates the analyst, invalidates
    sessions, disables/narrows the remote access policy, and verifies denial.
11. Evidence is sealed externally and reviewed with the focused validators and
    the full pilot validator.

## Approval checklist

- [ ] Approved analyst identity is externally verified and bound to the run.
- [ ] Identity provider/MFA and device policy are approved.
- [ ] One synthetic tenant, one analyst, one bounded expiry, and one approved
      scenario set are recorded.
- [ ] Security/release owner approved the access method and remote endpoint.
- [ ] Backup and isolated restore owner approved the staging recovery proof.
- [ ] Audit/provenance owner confirmed event availability and custody.
- [ ] Rollback owner and escalation contact are available.
- [ ] No production credentials, routes, databases, or data are in scope.

## Evidence collection workflow

Evidence is collected in three separate classes:

1. `rehearsal`: disposable procedure or tooling checks. Never pilot proof.
2. `remote_access_preflight`: private path, TLS, origin, identity-policy, and
   boundary checks before authentication. Never analyst behavior proof.
3. `authenticated_controlled_analyst_pilot`: real approved analyst actions,
   denials, audit/provenance observations, and revocation.

The access evidence contract is
`deployment/staging/GATE5_ANALYST_ACCESS_EVIDENCE.schema.json`. The final
authenticated pilot record must also satisfy
`deployment/staging/CONTROLLED_ANALYST_PILOT_EVIDENCE.schema.json` and the
five focused validators. A record is not `VERIFIED` merely because the
endpoint is healthy or access policy is configured.

Record only:

- run ID, source commit, access method, origin, UTC timestamps;
- opaque approved identity, tenant, authorization, audit, provenance, and
  custody references;
- PASS/BLOCKED/NOT_MEASURED control statuses and direct observations;
- evidence hashes and external custody receipt references.

Never record credentials, cookies, CSRF values, bearer tokens, session IDs,
database rows, customer data, private keys, tunnel tokens, or raw sensitive
payloads.

## Revocation and emergency response

On any unexpected access, origin drift, TLS failure, cross-tenant leakage,
audit/provenance gap, secret exposure, provider drift, or unmeasured gate:

1. Stop analyst activity.
2. Revoke authorization and deactivate the analyst.
3. Invalidate active sessions and verify post-revocation denial.
4. Disable the Tailscale grant/Serve listener and revoke the analyst device
   access.
5. Preserve only safe hashes and opaque references in external custody.
6. Notify the release/security owner and restart only with new approval and run
   ID.
