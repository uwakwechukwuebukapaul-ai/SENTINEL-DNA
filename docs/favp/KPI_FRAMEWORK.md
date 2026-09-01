# FAVP KPI Framework

**Status:** Proposed measurement framework
**Owner:** [Named measurement owner]
**Reporting cadence:** [Per session / weekly / phase close]

This framework defines measurements to support program decisions. It does not
claim that any target has been met. Targets, thresholds, and interpretation
must be approved before measurement begins.

## Measurement principles

- publish numerator, denominator, cohort, scenario versions, and missing data;
- separate observed behavior from participant perception;
- report confidence and limitations for small samples;
- do not use agreement with advisory output as a correctness proxy by itself;
- do not reward unsafe behavior, bypass attempts, or suppression of uncertainty;
- treat security stop events as control signals, not merely usability failures;
- preserve analyst decision authority in every measure;
- use synthetic data only.

## KPI catalogue

| KPI | Definition | Evidence source | Interpretation guardrail |
| --- | --- | --- | --- |
| Scenario completion rate | Completed approved scenarios Ã· started approved scenarios. | Session register and closeout records. | Report exclusions and blocked sessions separately. |
| Evidence completeness rate | Sessions meeting all required evidence fields Ã· sessions reviewed. | Evidence validator and reviewer checklist. | Missing fields may indicate workflow or training gaps; do not infer product quality alone. |
| Provenance traceability rate | Material findings with a verifiable source/timestamp/scope reference Ã· material findings reviewed. | Evidence/provenance records. | A reference must be checked, not merely present. |
| Tenant-boundary pass rate | Observed boundary checks passing Ã· boundary checks performed. | Tenant-isolation evidence and access logs. | Any critical unauthorized access is escalated regardless of aggregate rate. |
| Denied-action coverage | Required denial scenarios performed Ã· required denial scenarios planned. | Scenario records and audit references. | Coverage is not the same as denial effectiveness. |
| Audit completeness rate | Sensitive actions with expected audit references Ã· sensitive actions performed. | Audit evidence and provenance records. | State sink availability and review limitations. |
| Analyst independent-conclusion rate | Scenarios with a recorded conclusion before advisory review Ã· scenarios where ordering was in scope. | Session timeline and scorecard. | Does not measure correctness. |
| Advisory challenge rate | Advisory outputs challenged or rejected Ã· advisory outputs presented. | Scorecards and session records. | A higher or lower rate is not inherently better; analyze reasons and outcomes. |
| Evidence-backed conclusion rate | Conclusions meeting the approved evidence rubric Ã· conclusions reviewed. | Scorecards and independent review. | Must disclose ambiguous scenarios and reviewer agreement. |
| Median time to evidence-backed conclusion | Median elapsed time from scenario start to recorded evidence-backed conclusion. | Timestamped session records. | Do not trade speed for boundary, evidence, or human-review controls. |
| Critical control stop count | Number of sessions stopped for a critical control condition. | Incident/stop register. | Every event requires review; do not normalize it through averaging. |
| Access revocation completion | Sessions with verified revocation and post-revocation check Ã· sessions closed. | Revocation evidence. | Missing verification remains a blocker. |
| Participant-reported workflow friction | Structured rating or coded issue frequency by dimension. | Scorecards and feedback forms. | Perception must be separated from observed control performance. |

## Leading indicators

Review before sessions begin:

- application and agreement completion;
- orientation completion;
- readiness and evidence-custody pass status;
- scenario ambiguity and accessibility review;
- facilitator calibration;
- approved analyst/tenant/scope records;
- revocation rehearsal status.

## Decision indicators

At phase close, review:

- unresolved critical or high-severity control observations;
- evidence/provenance gaps;
- tenant-boundary and audit findings;
- independent analyst conclusions and uncertainty handling;
- advisory disagreements and corrections;
- access and revocation outcomes;
- sample composition, missing sessions, and scenario coverage;
- remediation ownership and re-test plan.

## Reporting template

For each reporting period, include:

- period and report version;
- cohort and scenario denominator;
- KPI values with numerator/denominator;
- missing or excluded observations;
- confidence/limitations statement;
- control exceptions and stop events;
- analyst quotes only when approved and de-identified;
- actions, owners, due dates, and re-test criteria.

No KPI should be published externally without review against the final
validation report and approved disclosure terms.

