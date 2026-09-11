# Gate 5 Analyst Access Validation Plan

## Plan metadata

Project: Sentinel DNA
Gate: Gate 5 Controlled Analyst Pilot
Status: PREPARED / PENDING EXTERNAL EXECUTION
Record timestamp: 2026-09-07T20:13:52.4214721Z
Prepared by: repository procedure review; no authentication was performed

Candidate commit: ca1d61467f4520f52a986e5fa1a8c13d499d2229
Candidate tree: 0c34089a3781c172c3711094b870f61964902d9

## Authentication entry point

Use the approved trusted-browser mechanism and the selected private Tailscale
path. The certified origin is exactly:

`https://uwakwe-desktop.taile388cc.ts.net`

Credentials must be supplied only through the approved browser authentication
bridge. No credential-bearing CLI, direct HTTP client, token, cookie, or session
value may be handled by the operator or written to evidence.

## Validation sequence

1. Confirm approved runtime, activation manifest, image digest, TLS CA, and
   certified origin through external custody.
2. Confirm manager authentication and active manager role through the browser.
3. Verify the missing-CSRF denial before any protected state change.
4. Provision or activate exactly one approved synthetic analyst and tenant
   through the protected workflow.
5. Verify server-derived analyst role, tenant scope, bounded expiry, secure
   cookies, and session behavior.
6. Execute the approved non-destructive synthetic investigation.
7. Verify analyst RBAC, privileged denials, foreign-tenant denial without
   leakage, audit/provenance linkage, and AI advisory-only behavior.
8. Revoke authorization, deactivate the analyst, invalidate sessions, and
   verify subsequent reads and writes fail closed.

## Controls

| Control | Required observation | Current status |
|---|---|---|
| MFA | Approved identity-provider/MFA event through external custody | PENDING |
| Trusted origin | CA/SNI-verified certified origin | BLOCKED locally |
| Session security | Secure cookie and bounded session evidence | PENDING |
| CSRF | Direct missing-CSRF denial | PENDING |
| Authorization | Analyst-only scope and privileged denials | PENDING |
| Tenant isolation | Foreign synthetic resource denied without leakage | PENDING |
| Audit/provenance | Opaque references with actor/role/tenant/action/correlation/time | PENDING |
| Revocation | Post-revocation fail-closed behavior | PENDING |

## Evidence and decision boundary

Only direct observations from a real authorized analyst run may be marked PASS.
Rehearsals, fixtures, configuration flags, health responses, and connectivity
alone do not establish analyst acceptance. Unperformed controls remain
`NOT_MEASURED` or `BLOCKED_WITH_REASON`.

This plan does not weaken authentication, authorize analyst access, establish
acceptance, or authorize production deployment.

## Status classification

READY: The approved browser-bound validation sequence and evidence boundary are
defined.

BLOCKED: Trusted-browser provider, certified origin, external identity, and
human approval are unavailable.

OWNER ACTION REQUIRED: Security/release owner must configure the approved
provider and authorize the real analyst run.

NOT MEASURED: Authentication, MFA, session, CSRF, RBAC, tenant, audit,
provenance, and revocation observations.
