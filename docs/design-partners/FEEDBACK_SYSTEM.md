# Design Partner Feedback System

## Purpose

Collect feedback that is specific, reproducible, security-aware, and useful to
both product decisions and commercial qualification. Feedback is not a promise
that a requested feature will be built.

## Weekly feedback template

**Partner:** [Reference]
**Week ending (UTC):** [Date]
**Scenario/session references:** [References]

- What did you attempt?
- What worked as expected?
- What was confusing, slow, incomplete, or unsafe?
- Which evidence or provenance was useful?
- Which evidence was missing or difficult to trust?
- Did you accept, challenge, or reject advisory output? Why?
- What would you change first?
- What should not change?
- Did you observe a boundary, tenant, audit, or access issue?
- What is the business impact, if any, and who owns it?
- Confidence in this feedback: `[Low/Medium/High]`
- Evidence references: `[References]`

## Feature-request workflow

1. Partner submits a request with problem, user, scenario, evidence, and
   desired outcome.
2. Program owner acknowledges without promising delivery.
3. Product/engineering triages value, scope, security, privacy, and effort.
4. Security owner reviews any access, data, evidence, or boundary implication.
5. Request is classified `DISCOVERY`, `PLANNED`, `IN_PROGRESS`, `DECLINED`, or
   `DUPLICATE` with rationale.
6. Partner receives a factual status update and any approved workaround that
   does not weaken controls.
7. Completed work is re-tested against the original scenario and evidence.

## Bug-report process

Required fields:

- non-secret report ID and severity;
- scenario/version and environment;
- reproducible steps using synthetic data;
- expected versus observed behavior;
- timestamps and evidence references;
- tenant/access scope;
- security impact and stop condition;
- workaround, if any, approved by security.

Do not include credentials, cookies, tokens, private keys, customer data, or
raw sensitive logs. Security-sensitive reports use the approved private channel,
not the general feedback channel.

## Usability survey

Rate 1â€“5 or `NOT_MEASURED`:

- task clarity;
- evidence discoverability;
- provenance understandability;
- workflow effort;
- confidence in scope and access boundaries;
- confidence in auditability;
- ease of challenging advisory output;
- overall usefulness for the stated workflow.

Include one example and one limitation for every low or high rating.

## Trust, confidence, and usefulness scoring

| Measure | Question | Interpretation |
| --- | --- | --- |
| Trust | â€œI can understand and review the evidence behind this workflow.â€ | Perception; not proof of correctness or security. |
| Analyst confidence | â€œI can make and explain my own decision from the available evidence.â€ | Human judgment measure; do not replace with system confidence. |
| AI usefulness | â€œThe advisory material helped me investigate or review.â€ | Utility perception; agreement does not equal correctness. |
| Evidence quality | â€œThe evidence was complete, attributable, and reproducible enough for this task.â€ | Requires references and reviewer context. |
| Workflow usability | â€œI could complete the approved task without avoidable friction.â€ | Report scenario, role, and assistance level. |

Use a defined survey version, response count, missing responses, and cohort
context. Do not average away a critical security stop.

## Required measures

Track the following separately:

- **TRUST:** structured trust score with evidence-quality context;
- **USAGE:** approved sessions, scenarios, and workflow steps completed;
- **EVIDENCE QUALITY:** source/provenance completeness and reviewer sufficiency;
- **TIME SAVINGS:** measured time difference against an approved baseline,
  with method and exclusions;
- **PAYMENT INTENT:** stated buyer interest or next-step intent, never inferred
  from usage or analyst enthusiasm.

## Feedback governance

- keep participant feedback attributable internally and de-identified for
  external use unless approved otherwise;
- distinguish feature requests from bugs, risks, and commercial objections;
- record dissent and negative feedback without retaliation;
- preserve the original analyst conclusion when editing summaries;
- link decisions to evidence and owner/date;
- do not publish a metric without denominator, method, and limitation.

