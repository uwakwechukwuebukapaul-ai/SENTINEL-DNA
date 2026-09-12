# Pilot Execution Framework

## Operating principles

The pilot is an evidence-producing evaluation with customer-approved scope. Analysts make the final decision. Recommendations are reviewed, recorded, and challenged; no workflow silently changes customer systems.

## Lifecycle

### Kickoff

Confirm scope, users, data, environments, integrations, evidence custody, audit requirements, success criteria, stop conditions, support, and communication channels. Reconfirm that production action, credentials, and unapproved data are out of scope.

### Weekly operating cadence

The weekly review should cover:

- Investigations attempted and denominator.
- Evidence generated, reviewed, rejected, or incomplete.
- Analyst usage, confidence, trust, and usefulness feedback.
- Blocked workflows, defects, scope changes, and security events.
- Audit and tenant-isolation exceptions.
- Decisions and named owners for the next period.

### Analyst feedback meeting

Use the feedback template in `FEEDBACK_SYSTEM.md`. Collect independent analyst observations before showing aggregate product interpretation. Record role, workflow, time period, evidence references, and whether the observation is fact, interpretation, or request.

### Investigation review

For each sampled investigation:

1. Record the case identifier and approved dataset.
2. Capture the analyst’s initial assessment before reviewing recommendations where practical.
3. Review recommendations, supporting evidence, provenance, uncertainty, and missing data.
4. Record the analyst’s final decision and rationale.
5. Record any customer action separately from Sentinel DNA output.
6. Preserve reviewer, timestamp, version, and disposition metadata.

### Evidence review

Reviewers check source identity, collection time, transformations, links between claims and evidence, completeness, access history, retention, and replay or reconstruction capability. “Not available” and “not measured” are valid results and must not be silently converted to success.

### AI recommendation review

The analyst must be able to reject, qualify, or defer a recommendation. Reviewers assess whether the output was explainable enough for the defined task, whether uncertainty was visible, and whether the evidence supported the recommendation. The review must not imply that an output is a final determination or a substitute for policy.

### Incident workflow testing

Use synthetic or explicitly approved test events. Test routing, escalation, evidence capture, audit records, and human approval points. Do not perform unauthorized containment, login automation, account creation, or production changes as part of a pilot exercise.

## Change control

Any request to add users, data, integrations, environments, or response actions is a scope-change request. The owner records impact to security, privacy, fees, schedule, evidence, and success criteria. Work waits for the required approval.

## Stop conditions

Pause the pilot for suspected data exposure, tenant boundary failure, unauthorized access, audit failure, evidence-integrity concern, unsafe recommendation behavior, unapproved scope, or a customer security owner’s instruction. Preserve relevant audit evidence, revoke or restrict access as appropriate, notify the agreed contacts, and resume only after documented approval.

## Closeout

The closeout package contains the methodology, scope and denominator, scorecards, evidence index, limitations, blocked workflows, security record, customer feedback, open actions, and decision. The possible decisions are:

- Stop and close.
- Extend with an approved change.
- Repeat a bounded validation.
- Prepare a paid continuation or annual subscription proposal.
- Prepare a separately approved enterprise expansion.

The customer’s decision and evidence, including a negative decision, are retained according to the agreement.
