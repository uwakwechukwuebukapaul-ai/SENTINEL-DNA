# Design Partner Technical Onboarding

**Environment:** private, controlled, non-production unless a separately
approved scope states otherwise
**Default data:** synthetic only

## Technical objectives

Provide a bounded environment in which partner analysts can perform approved
validation activities while Sentinel DNA preserves tenant isolation, evidence
provenance, auditability, human authority, and fail-closed behavior.

## Controlled tenant architecture

```text
approved partner identity
        |
private access boundary
        |
partner-scoped Sentinel DNA tenant
        |
synthetic dataset + approved scenarios
        |
evidence/provenance and audit records
        |
controlled custody and reviewer access
```

Required properties:

- one named partner scope per approved evaluation;
- one or more explicitly approved synthetic tenants, with a documented reason
  for each;
- analyst role and tenant scope derived by the application, not by client
  claims;
- no production control-plane or customer-data connection;
- private TLS access through the approved boundary;
- time-limited, personal, revocable access;
- cross-tenant and privileged-action denial checks;
- audit and provenance records available to authorized reviewers.

## Dataset policy

### Synthetic data

Synthetic data is the default and should include realistic structure without
real identities, secrets, customer records, harmful samples, or live
infrastructure references.

### Sanitized data

Sanitized data is not automatically approved. If proposed, record source,
sanitization method, re-identification review, fields retained, owner,
retention, deletion, and written security/privacy approval before import.

### Prohibited material

Do not import credentials, cookies, tokens, private keys, customer data,
production logs, personal data, regulated data, live incident data, or browser
session exports.

## Workspace access

Before access:

- verify the named analyst and agreement status;
- confirm approved tenant, scenarios, time window, and support contact;
- complete the trusted-browser and staging readiness workflow where required;
- confirm audit logging and evidence custody;
- record access issuance reference without recording credentials.

During access, the analyst may see only the approved workspace and scenario
surfaces. Unexpected access is a stop condition.

## Evidence collection process

For every scenario capture:

- non-secret run and scenario identifiers;
- UTC start/end times;
- analyst and tenant scope references;
- evidence source references and provenance;
- independent analyst conclusion, confidence, and missing evidence;
- advisory-output comparison and reason for acceptance/challenge/rejection;
- denied-action and control observations;
- reviewer status, limitations, and follow-up owner.

Evidence must be append-only by procedure, access-controlled, hash-verifiable,
and free of credentials, cookies, tokens, private keys, raw customer data, and
browser sessions.

## Feedback telemetry

Collect only approved non-secret telemetry needed to understand workflow:

- scenario start/stop and completion events;
- navigation/action categories within the approved scope;
- evidence-reference creation and review events;
- denial, error, and stop events;
- time intervals needed for the KPI framework;
- explicit analyst feedback and scores.

Do not collect content beyond the approved dataset or use telemetry as a proxy
for analyst correctness. Telemetry access, retention, and deletion require
approval.

## Audit logging

Verify audit records for access issuance, tenant scope, scenario activity,
sensitive actions, denied actions, evidence references, advisory review,
revocation, and post-revocation checks. Audit references must be tenant-scoped
and reviewable without exposing secret material.

## Access revocation

At session or engagement close:

1. revoke the named analyst's authorization;
2. invalidate active sessions through the approved control path;
3. remove or disable the partner scope as approved;
4. verify workspace and cross-tenant access fail closed;
5. close the external browser/runtime session through its reviewed lifecycle;
6. preserve non-secret audit and evidence references;
7. record revocation owner, reason, timestamp, and verification result.

## Technical readiness record

| Check | Status | Evidence/reference |
| --- | --- | --- |
| Private access boundary | [PASS/BLOCKED] | [Reference] |
| Synthetic dataset approved | [PASS/BLOCKED] | [Reference] |
| Tenant isolation verified | [PASS/BLOCKED] | [Reference] |
| Audit logging available | [PASS/BLOCKED] | [Reference] |
| Evidence custody ready | [PASS/BLOCKED] | [Reference] |
| Revocation tested | [PASS/BLOCKED] | [Reference] |

