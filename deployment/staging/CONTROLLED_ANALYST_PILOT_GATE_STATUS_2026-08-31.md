# Controlled analyst pilot gate status — 2026-08-31

## Readiness report

Boundary closure: `PASS`.

Controlled analyst pilot authorization: `BLOCKED_WITH_REASON` (`0%`, 0 of 14
authenticated gates passed). No analyst account, credential, or URL was
created or issued.

Verified boundary/runtime results:

- `sentinel-dna-staging` resolves through the system resolver only to
  `127.0.0.1`.
- The reviewed override is exactly `127.0.0.1:18443:443`.
- The live pilot publication is exactly `127.0.0.1:18443->443/tcp`.
- No running container publishes `0.0.0.0:443`, `0.0.0.0:8443`, or any other
  host port. The separate wildcard deployment edge remains stopped.
- Docker Engine `29.7.2` is available; the pilot Compose project is
  `sentinel-dna-pilot-974e327`.
- Pilot app, PostgreSQL, and Redis have no host ports. The pilot
  `staging_internal` network is `internal=true`.
- The mounted certificate validates as TLS 1.3 with SANs
  `DNS:sentinel-dna-staging`, `IP Address:127.0.0.1`, and
  `IP Address:192.168.1.115`.
- Certificate-backed `/health` and `/ready` both return HTTP 200.
- Staging contract tests pass: `23 passed`.

## Remaining blockers report

The following gates remain `NOT_MEASURED` and prevent release readiness:

`manager_authentication`, `csrf_protection`, `analyst_rbac`,
`tenant_isolation`, `audit_logging`, `provenance_verification`,
`investigation_workflow`, `ai_advisory_only`, `deny_cross_tenant`,
`deny_admin_escalation`, `deny_database`, `deny_shell_container`,
`deny_destructive`, and `session_revocation`.

Also outstanding are creation and verification of exactly one synthetic
tenant and exactly one synthetic analyst, tenant-scoped audit/provenance
references, all revocation results, and human release approval. The trusted
browser inventory is currently empty, so secure manager authentication cannot
be performed.

## Exact next manual validation steps

1. Connect the approved trusted browser service. Do not use standalone browser
   automation or direct credential-bearing HTTP calls.
2. Through the private loopback origin, authenticate the manager using the
   secure handoff. Verify `/api/auth/me` is `admin` or `soc_manager` and prove
   a missing-CSRF manager write returns `403` without state change.
3. After explicit operator approval, create exactly one synthetic tenant and
   exactly one synthetic analyst. Verify the analyst has only role `analyst`,
   only the synthetic tenant, and a bounded authorization expiry.
4. Transfer activation out-of-band. Activate the analyst without recording
   credentials, cookies, CSRF values, or activation tokens.
5. Validate analyst authentication, RBAC, tenant isolation, synthetic
   investigation workflow, tenant-scoped audit/provenance, and AI
   advisory-only/human-review enforcement.
6. Exercise and record denial results for cross-tenant access, admin
   escalation, database, shell/container, and destructive actions. Any
   ambiguous or untested result is not `PASS`.
7. Revoke authorization, deactivate the analyst, invalidate sessions, and
   verify post-revocation reads and writes fail closed.
8. Create a new secret-free, append-only evidence file with every required
   gate marked `PASS`, then run the unchanged validator against that file.
9. Only if the validator returns exactly
   `READY_FOR_CONTROLLED_ANALYST_PILOT` may the human release authority
   consider the later private access procedure. Until then, keep the URL
   unissued.
