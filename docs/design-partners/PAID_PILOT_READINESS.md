# Design Partner Paid Pilot Readiness

**Decision vocabulary:** `READY_FOR_PAID_PILOT_PROPOSAL`,
`BLOCKED_WITH_REASON`, or `NOT_MEASURED`
**Authority:** named human program, security, and commercial owners

This checklist determines whether a design partner is ready to receive a paid
pilot proposal. It does not approve a pilot, grant access, or create a
subscription.

## Partner and business readiness

- [ ] Partner tier and selection record are complete.
- [ ] FAVP/design-partner validation scope and evidence are reviewed.
- [ ] Business problem and decision owner are documented.
- [ ] Named analyst, security owner, executive sponsor, and procurement owner
      are identified.
- [ ] Proposed paid-pilot decision criteria are measurable and scoped.
- [ ] No outcome, savings, revenue, or customer claim is being inferred.

## Legal and commercial readiness

- [ ] Design Partner Agreement status is recorded.
- [ ] NDA/confidentiality relationship is clear.
- [ ] Data usage, IP, feedback, publication, retention, and deletion terms are
      reviewed.
- [ ] Paid pilot scope, duration, fees, billing, support, and change control are
      drafted using approved commercial terms.
- [ ] Customer procurement and legal path is identified.
- [ ] Pilot transition is a separate explicit decision; no automatic conversion.

## Security and technical readiness

- [ ] Data boundary is synthetic or separately approved sanitized data.
- [ ] Tenant, analyst, role, scenario, and time scope are documented.
- [ ] Private access, identity, least privilege, and revocation controls are
      approved.
- [ ] Tenant isolation and privileged-action denial evidence are reviewed.
- [ ] Audit logging and provenance requirements are understood and testable.
- [ ] Evidence custody, retention, deletion, and access controls are approved.
- [ ] Incident, stop, rollback, and revocation owners are named.
- [ ] No credentials, cookies, tokens, private keys, or browser sessions are
      stored in program records.

## Customer success readiness

- [ ] Onboarding, support, training, and communication cadence are defined.
- [ ] Baseline and measurement method are agreed.
- [ ] Customer responsibilities and Sentinel DNA responsibilities are explicit.
- [ ] Exit, rollback, data deletion, and renewal review are documented.
- [ ] Customer acceptance and final review process is defined.

## Decision record

| Area | Status | Evidence/reference | Owner |
| --- | --- | --- | --- |
| Partner qualification | [Status] | [Reference] | [Owner] |
| Validation evidence | [Status] | [Reference] | [Owner] |
| Business case | [Status] | [Reference] | [Owner] |
| Legal/commercial | [Status] | [Reference] | [Owner] |
| Security/technical | [Status] | [Reference] | [Owner] |
| Customer success | [Status] | [Reference] | [Owner] |
| Final decision | [Status] | [Reference] | [Owner] |

## Blocker policy

Any unresolved security, data, access, evidence, legal, or ownership blocker
produces `BLOCKED_WITH_REASON`. Do not remove a blocker to meet a commercial
date. A new proposal requires updated evidence and approvals if material scope
changes.

