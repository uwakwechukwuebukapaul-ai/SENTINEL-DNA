# Controlled Operational Pilot Validation

The operational pilot converts enterprise proof into bounded operational
evidence. It runs synthetic alerts for tenants A, B, and C through a
deterministic execution adapter that consumes the existing normalized
investigation evaluation fixtures. It does not replace or modify the
production investigation path.

```text
Tenant A/B/C synthetic alerts
             |
             v
       Alert ingestion
             |
  Coordinator / Orchestrator contract projection
             |
  Evidence -> IOC -> MITRE -> memory -> reasoning -> report
             |             |
             |             +--> advisory investigation + organizational context
             +--> provenance events + analyst feedback
             |
       Immutable pilot report
       metrics + audit hashes + replay digest + safety checks
```

## Controlled execution

The pilot supports synthetic alert ingestion, bounded investigation execution,
evidence collection, investigation-memory and organizational-memory usage
tracking, analyst feedback capture, and replay verification. One controlled
synthetic evidence-provider failure is included so successful and failed
investigation metrics are both exercised. Failed execution terminates without
an enforced verdict and remains fail-closed.

The timing model is deterministic synthetic timing, not host wall-clock
measurement. This makes repeated pilot runs comparable and keeps the replay
digest stable. Deployment-level performance testing remains a separate step.

## Operational metrics

Reports include completed, successful, and failed investigations; mean/p50/p95
investigation latency; mean evidence retrieval, IOC enrichment, MITRE mapping,
memory retrieval, organizational-memory retrieval, and report-generation
timings; memory item counts; context reuse rate; and analyst feedback count.

## Evidence and security boundaries

- Every alert, evidence item, memory observation, feedback record, and audit
  event carries tenant and investigation scope.
- Provenance events form a hash chain. Each event records its previous hash and
  its own audit hash; report-level execution records form a second chain.
- Cross-tenant data is never used by a pilot execution. Tenant leakage and
  provenance mismatches fail validation.
- `InvestigationResult` keys are compared with the canonical result envelope.
- Authorization status, fail-closed behavior, and enforced verdict remain
  unchanged across memory use.
- Memory is advisory-only and no autonomous response action is executed.
- Report writes are append-only: an existing output path is rejected rather
  than overwritten.

## Run and replay

```text
python scripts/run_operational_pilot.py --generated-at 2026-08-25T00:00:00+00:00
python scripts/run_operational_pilot.py --output artifacts/operational-pilot.json
```

The CLI executes the pilot twice and refuses success if the replay digests
differ. The report includes an immutable content digest, while the replay
digest excludes issuance time so repeated validation of the same fixtures is
stable.

## Future controlled expansion

Production replay adapters may later feed redacted alert and analyst-review
records into `PilotAlert` and the normalized evaluator. Any such adapter must
retain tenant scope, provenance, append-only evidence, and the same
authorization/verdict safety invariants. No vector store, embedding model, or
autonomous response path is required for this milestone.

## Controlled real-analyst pilot preparation

The synthetic operational pilot above is not a real-analyst evaluation. A
separate, bounded pilot may use the existing analyst workspace and canonical
investigation APIs only after an authorized operator records:

- one unique least-privilege analyst identity;
- one isolated non-production tenant and environment;
- synthetic or explicitly approved non-customer data;
- pilot authorization, owner, start date, and end date in UTC;
- a reversible access/revocation procedure; and
- an incident/escalation contact and protected evidence destination.

The bounded pilot owner may be `Uwakwe chukwuebuka paul`. That assignment is
limited to pilot operation and does not assign enterprise production
ownership, on-call responsibility, an enterprise SLA, independent approval,
customer approval, compliance approval, security approval, or third-party
approval.

### Existing workflow boundary

The pilot reuses the existing session authentication, RBAC, canonical tenant
resolution, CSRF protection, analyst workspace/read model, provenance, audit,
and append-only analyst-feedback services. The analyst workflow is:

`sign in → tenant-scoped workspace → synthetic alert → investigation →
evidence/relationships/intelligence/MITRE/uncertainty/provenance review →
independent analyst conclusion or note → append-only feedback/audit event →
report inspection/export → sign out`

The execution path remains:

`InvestigationCoordinator → InvestigationOrchestrator → RuntimeTaskExecutor`

The pilot does not add a second investigation route, elevate advisory AI
output into an enforced verdict, or grant unrestricted SOAR, command, or
destructive privileges. The analyst feedback API attributes actor and tenant
server-side and does not permit the request to select another case, tenant, or
actor.

### Scenario and measurement rules

The first pilot set must include phishing compromise, suspicious
authentication, malware execution, suspicious IP/domain, contradictory
intelligence, and benign false positive. Use existing approved synthetic
fixtures; do not invent a finding or analyst conclusion. The existing
operational-accuracy catalog covers the first, second, third, contradictory,
and benign classes. A suspicious IP/domain fixture must be identified and
approved before execution if it is not already present in the selected set.

For every assigned scenario, capture the human conclusion independently from
the AI conclusion, analyst and AI confidence, evidence used by each, the
agreement/disagreement, measured time-to-conclusion when available,
false-positive/false-negative observations, missing evidence, contradictions,
feedback, usability issues, investigation/alert identifiers, feedback and
audit references, and provenance references. Unobserved values remain
`NOT MEASURED` or `NOT RECORDED`; disagreements are retained.

### Real-analyst evidence contract

The evidence artifact must be append-only and contain only non-secret data.
Its minimum fields are `pilot_id`, `run_id`, `status`, exact analyst
identifier or approved pseudonym, owner, isolated environment, tenant,
planned and actual UTC timestamps, immutable application commit, scenario
entries, investigation and alert identifiers, actions, outcomes, evidence,
feedback/audit/provenance references, test/result metadata, data-classification
controls, and a final SHA-256 digest. The record must explicitly state
`customer_data=false`, `credentials_or_tokens=false`,
`production_impact=false`, and `external_notification=false`.

Before execution the capture template remains `NOT_EXECUTED`; it must not be
reported as a completed analyst pilot. The repository's monitoring evidence
(`MONITOR-PILOT-001`) remains separate bounded synthetic evidence and cannot
be upgraded into real-analyst, enterprise, or production readiness evidence.

### Security and reversibility gate

Preparation is blocked until the operator verifies authentication,
least-privilege authorization, tenant isolation, secure session/cookie and
CSRF behavior, input/output handling, secret exclusion, disabled production
debug behavior, fail-closed authorization, absence of unintended external
network actions, and absence of unrestricted/destructive execution. At pilot
end or on incident, deactivate the pilot user and revoke sessions using the
existing auth-service path, preserve the append-only record, and escalate only
through the approved protected channel.

### Remote analyst handoff and access gates

The repository now composes a durable `pilot_authorizations` boundary with
the existing authentication, canonical authority, tenant membership, RBAC,
CSRF, audit, workspace, investigation, provenance, and feedback services.
When `SENTINEL_DNA_PILOT_ACCESS_REQUIRED=1`, an analyst must have one active,
unexpired, non-revoked authorization for the resolved tenant. Creation and
revocation are manager-only, server-bind the authorizer and tenant, accept
only the existing approved scenario catalog, write audit events, and revoke
the target's sessions. Investigation and feedback activity is correlated to
the authorization through the existing canonical investigation APIs.

### Controlled account provisioning boundary

The remote pilot account is provisioned only by an authenticated founder or
authorized `admin`/`soc_manager`; there is no public or self-service
registration path for this pilot. `POST /api/pilot-provisioning` derives the
manager and manager tenant from the authenticated session and accepts only a
bounded expiry, unique analyst identity, isolated pilot-tenant name, and
approved synthetic scenario IDs. It creates the dedicated pilot tenant,
canonical analyst identity, inactive analyst authentication record, pilot
authorization, and one-time activation record in one transaction. The
activation token is returned only once to the manager-controlled response,
stored only as a hash, and must be transferred through a protected channel;
it is never logged or included in evidence. The analyst activates their own
credential through `POST /api/pilot-provisioning/activate`, after which the
existing authentication/session and RBAC boundary applies.

The authorization binds the analyst role, isolated tenant, approved scenario
allowlist, manager actor, UTC start/expiry, revocation state, and audit
correlation. Unknown, expired, revoked, missing, role-mismatched, and
cross-tenant records are denied. Manager-only list, detail, and revocation
operations are protected by the existing permission and CSRF controls.
Revocation deactivates the account, invalidates sessions, revokes the
authorization and pilot tenant, blocks further pilot investigations and
feedback, and preserves the audit/provenance history. No provisioning path
grants repository/GitHub, shell/SSH, database, production-secret,
administrator, SOAR, or destructive-action privileges.

`REMOTE_ANALYST_ENDPOINT = NOT PROVIDED`. This application capability does
not establish remote accessibility. An approved private non-production HTTPS,
VPN, or zero-trust front door remains a separate infrastructure prerequisite;
the development server must not be exposed directly to the Internet.

Founder handoff sequence:

1. Provision one analyst account with `POST /api/pilot-provisioning`, transfer
   the one-time activation token through a protected channel, and have the
   analyst activate their own credential.
2. Confirm the resulting authorization, isolated pilot tenant, expiry,
   approved scenario IDs, and audit correlation ID through the manager view.
   The existing `POST /api/pilot-authorizations` path remains available only
   for an already-created active analyst account.
3. Provide the analyst the verified application URL through a protected
   channel. Do not provide repository, GitHub, shell, SSH, database,
   production-secret, or administrator access.
4. After the analyst run, review audit/provenance evidence and revoke with
   `POST /api/pilot-authorizations/<authorization_id>/revoke`.

No remote endpoint is configured or verified by this repository. Remote
accessibility is a separate infrastructure gate requiring an approved
private HTTPS, VPN, or zero-trust front door; a public development-server
exposure is prohibited. The real-analyst evidence record remains
`NOT_EXECUTED` until an actual external analyst performs the workflow.
