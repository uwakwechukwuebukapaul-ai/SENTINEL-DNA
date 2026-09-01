# Customer Onboarding System

Onboarding is a security and commercial gate. No pilot access is granted until the applicable checklist is complete and the customer’s authorized owner accepts the record.

## 1. Customer intake checklist

- `[ ]` Customer legal entity, tenant name, region, sponsor, security owner, analyst lead, and procurement contact recorded.
- `[ ]` Use case, workflows, environments, integrations, data classes, and evidence volume bounded.
- `[ ]` Package, dates, fees, support, success criteria, and stop conditions approved.
- `[ ]` Authorized users and roles supplied through the approved identity process.
- `[ ]` Security questionnaire and privacy/data review complete.
- `[ ]` Tenant isolation and audit requirements accepted.
- `[ ]` Evidence custody, retention, export, and deletion owners identified.
- `[ ]` Incident escalation, support, and change contacts confirmed.
- `[ ]` Access revocation and closeout plan recorded.

## 2. Security questionnaire

The customer security owner must answer, or explicitly mark not applicable:

| Area | Questions |
|---|---|
| Data | What data classes are in scope? Is the initial dataset synthetic or sanitized? Are production records prohibited? |
| Identity | Which identity provider and MFA policy apply? Who approves and reviews access? |
| Tenant | How is the tenant boundary verified? Which roles may view, export, or approve evidence? |
| Integrations | Which systems are in scope? What is the approved direction and least-privilege permission set? |
| Audit | Which actions, user identities, timestamps, and evidence events must be logged? Where are logs retained? |
| Evidence | Who is the custodian? What retention, export, integrity, and deletion rules apply? |
| Incident | How are suspected data exposure, misuse, or control failures reported and contained? |
| Privacy | Are there residency, privacy, retention, or customer-approval constraints? |
| Exit | Who revokes users, closes integrations, and signs the final disposition? |

Unanswered questions are blockers, not implied approvals.

## 3. Tenant provisioning workflow

1. Confirm signed commercial and security approvals.
2. Create or designate the customer tenant through the approved control plane.
3. Bind the tenant to the approved environment and scope.
4. Configure customer-approved identity and MFA; never request or store passwords in pilot artifacts.
5. Create least-privilege roles and named users.
6. Load only the approved synthetic or sanitized dataset.
7. Configure audit events, retention, evidence custody, and export controls.
8. Run tenant-isolation and unauthorized-access checks.
9. Record a readiness decision with owner, timestamp, and evidence references.
10. Grant access only after the decision is `READY_FOR_ANALYST_PILOT` or its customer-approved equivalent.

## 4. RBAC setup

Use named identities and separate roles for analyst, reviewer, sponsor, security administrator, support, and auditor as applicable. A role must have only the permissions required for the agreed workflow. Review and remove unused access at each scheduled review and at closeout.

No role may:

- Export secrets or authentication material.
- Cross tenant boundaries.
- Change audit records or evidence provenance.
- Approve its own high-impact action without the customer’s required separation of duties.
- Turn an advisory recommendation into an automatic response.

## 5. Audit configuration

Before the first investigation, verify that the audit record captures at least user identity, tenant, event type, timestamp, target or evidence reference, outcome, and correlation identifier as applicable. Record the log destination, retention, reviewer, and tamper or integrity controls in the onboarding record.

## 6. Evidence custody setup

Define the evidence record identifier, source, collection time, transformation history, reviewer, access history, retention, export format, and disposition. Keep customer evidence in the approved tenant or custody location. Do not place credentials, cookies, tokens, or browser sessions in evidence or documentation.

## 7. Analyst onboarding

The analyst receives:

- Scope, roles, data rules, and support path.
- AI limitation and human-decision briefing.
- Evidence review and provenance instructions.
- Escalation and stop-condition instructions.
- A synthetic-data orientation exercise.
- Confirmation that access is personal, time-bounded, and revocable.

The analyst must acknowledge that Sentinel DNA output is advisory and that customer procedures govern any action.

## 8. Readiness gate

The onboarding owner records `READY`, `BLOCKED_WITH_REASON`, or `NOT_STARTED`. A missing approval, failed isolation check, missing audit evidence, unbounded data, invalid identity, or unresolved critical vulnerability is a blocker. Do not begin a pilot to discover whether a prerequisite was met.

## 9. Onboarding record

| Field | Value |
|---|---|
| Customer / tenant | `[Customer-approved value]` |
| Package / order form | `[Reference]` |
| Security owner | `[Named owner]` |
| Data decision | `[Synthetic / sanitized / separately approved]` |
| RBAC evidence | `[Reference]` |
| Tenant isolation evidence | `[Reference]` |
| Audit evidence | `[Reference]` |
| Evidence custody | `[Location and owner]` |
| Readiness decision | `[Decision, code, timestamp]` |
| Revocation owner/date | `[Owner / planned date]` |
