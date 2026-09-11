# Gate 5 Controlled Analyst Pilot Execution Framework

## Status and scope

Gate 4 infrastructure is complete at commit
`fa8aa1fef3010beb00dff84bd7f76fec4e0fbaaf`, with the certified staging origin
and all 13 Gate 4 readiness checks passing. This document prepares the next
execution phase; it does not claim production readiness.

The Gate 5 target is:

`READY_FOR_CONTROLLED_ANALYST_PILOT_EXECUTION`

That target may be recorded only after one real, authenticated, bounded,
human-reviewed staging pilot has produced complete evidence. Existing
rehearsal records and Gate 4 infrastructure evidence cannot be promoted to
authenticated pilot evidence.

## Architecture impact analysis

No production architecture or application runtime behavior is changed by this
framework. The additions are release-engineering controls around the existing
staging deployment:

| Area | Impact | Security boundary |
| --- | --- | --- |
| Application/runtime | None | Existing authorization, tenant, audit, provenance, and revocation behavior remains authoritative. |
| Trusted browser/provider | None | Gate 4 custody, certified origin, and browser-auth bridge remain unchanged. |
| Evidence collection | Adds a schema and read-only validators | Validators inspect operator-captured records only; they cannot authenticate or mutate the service. |
| Evidence custody | Adds explicit class and provenance fields | External custody remains the source for credentials, browser sessions, backups, and runtime bundles. |
| Operations | Adds a first-pilot sequence and stop conditions | Every unperformed or unobserved control remains blocked or not measured. |
| Tests | Adds contract tests for fail-closed evidence decisions | Test fixtures are in memory and are not pilot evidence. |

The workflow is:

```text
approved staging + trusted browser
        -> real operator authentication and bounded analyst actions
        -> non-secret observations and custody references
        -> append-only external evidence record
        -> five focused validators + full evidence validator
        -> human release/security decision
```

The validators do not accept credentials, cookies, tokens, screenshots with
secrets, direct database output, or synthetic approval records. They also do
not turn a health response, configuration flag, rehearsal, or test fixture
into behavioral proof.

## Evidence classes and custody

| Evidence class | Purpose | Can satisfy Gate 5? |
| --- | --- | --- |
| `rehearsal` | Validate procedures, disposable storage behavior, schema handling, or operator familiarity without real authentication. | No. Retain as rehearsal only. |
| `gate4_infrastructure` | Prove provider custody, runtime/image identity, certified origin, and staging readiness. | No. Required prerequisite, not analyst behavior proof. |
| `authenticated_controlled_analyst_pilot` | Record one real, approved, synthetic-data-only analyst run in staging, including denials and revocation. | Yes, only after human review and all validators pass. |

Authenticated pilot evidence must include a unique run ID, source commit, UTC
times, one synthetic tenant and analyst identifier, certified boundary
observations, direct gate observations, opaque custody references, audit and
provenance references, revocation results, and a human decision. It must not
include credentials, authentication material, cookie/session values, customer
data, database rows, or private runtime contents.

The authoritative schema is
`deployment/staging/CONTROLLED_ANALYST_PILOT_EVIDENCE.schema.json`. A record
with `evidence_class: rehearsal` is intentionally rejected by the focused
validators.

## Controls and exit criteria

The five focused validators cover these evidence obligations:

1. Authenticated analyst access: manager session and analyst role/access are
   directly observed.
2. RBAC enforcement: CSRF protection, analyst RBAC, and privileged/database,
   shell, and destructive denials are directly observed.
3. Tenant isolation: the analyst remains in the approved tenant and a known
   foreign-tenant request is denied without leakage.
4. Audit trail: sensitive actions, denials, provenance, and advisory-only AI
   handling have non-secret references and complete coverage.
5. Session revocation: authorization revocation, deactivation, session
   invalidation, and post-revocation fail-closed behavior are observed.

The focused validators are necessary but not sufficient by themselves. The
full manual evidence validator, fresh staging backup/restore proof, Gate 4
readiness result, boundary/TLS checks, custody review, and human approval are
also required. Any failure, missing reference, secret-shaped value, stale
identity, or `NOT_MEASURED` result keeps the decision blocked.

## Rehearsal separation

Rehearsal may exercise the operator sequence and validator plumbing with
disposable data, but it must be stored outside the authenticated pilot
evidence namespace or explicitly labeled with its rehearsal class. It must
not contain fake analyst approval, fake authentication, fabricated audit
events, or an invented release decision. The PostgreSQL rehearsal currently
retained in external custody explicitly records backup/restore as not
executed and therefore remains non-pilot evidence.

## Files in this framework

- `deployment/staging/CONTROLLED_ANALYST_PILOT_EVIDENCE.schema.json` — strict
  non-secret authenticated pilot evidence contract.
- `deployment/staging/scripts/controlled_analyst_pilot_evidence_validation.mjs`
  — shared read-only fail-closed validation rules.
- `deployment/staging/scripts/validate_authenticated_analyst_access.mjs`
- `deployment/staging/scripts/validate_analyst_rbac.mjs`
- `deployment/staging/scripts/validate_tenant_isolation.mjs`
- `deployment/staging/scripts/validate_audit_trail.mjs`
- `deployment/staging/scripts/validate_session_revocation.mjs` — focused CLI
  validators; each exits non-zero unless its control is directly evidenced.
- `deployment/staging/scripts/validate_manual_analyst_pilot_evidence.mjs` —
  existing full-record validator tightened to require the authenticated pilot
  evidence class and to keep parse/read failures secret-safe.
- `tests/staging/controlled_analyst_pilot_evidence_validation.test.mjs` —
  contract and fail-closed tests using in-memory fixtures only.
- `deployment/staging/GATE5_CONTROLLED_ANALYST_PILOT_EXECUTION_RUNBOOK.md` —
  exact operator sequence and stop/rollback procedure.

The existing Gate 4 handoff, Gate 4 readiness artifact, manual pilot runbook,
and execution-readiness checklist remain retained references. No generated
runtime bundle, external custody content, credential, backup, browser session,
or synthetic production artifact belongs in Git.
