# FAVP Analyst Scorecard

**Scorecard version:** 1.0
**Participant:** [Identifier]
**Session/run ID:** [Non-secret identifier]
**Scenario:** [Identifier/version]
**Reviewer:** [Name or identifier]
**Date/time (UTC):** [Timestamp]

This scorecard records observations; it does not produce a professional
designation or an assurance result. Use `NOT_MEASURED` when evidence is absent.

## Rating scale

| Score | Meaning |
| --- | --- |
| 1 | Materially prevented or unsafe within the approved scenario. |
| 2 | Partially completed with substantial assistance, ambiguity, or control friction. |
| 3 | Completed with observable gaps or moderate assistance. |
| 4 | Completed independently with minor gaps or friction. |
| 5 | Completed independently with clear, reproducible evidence and no observed gap. |
| `NOT_MEASURED` | The criterion was not observed or evidence was insufficient. |

Scores require an evidence reference and a note. A high score does not override
a security stop condition or a failed access boundary.

## Core dimensions

| Dimension | Rating | Evidence reference | Observation |
| --- | --- | --- | --- |
| Scope comprehension | [1â€“5/NOT_MEASURED] | [Reference] | [Note] |
| Evidence discovery | [1â€“5/NOT_MEASURED] | [Reference] | [Note] |
| Evidence interpretation | [1â€“5/NOT_MEASURED] | [Reference] | [Note] |
| Provenance traceability | [1â€“5/NOT_MEASURED] | [Reference] | [Note] |
| Uncertainty recognition | [1â€“5/NOT_MEASURED] | [Reference] | [Note] |
| Reproducibility of reasoning | [1â€“5/NOT_MEASURED] | [Reference] | [Note] |
| Tenant-boundary understanding | [1â€“5/NOT_MEASURED] | [Reference] | [Note] |
| Denied-action handling | [1â€“5/NOT_MEASURED] | [Reference] | [Note] |
| Advisory-output challenge | [1â€“5/NOT_MEASURED] | [Reference] | [Note] |
| Human decision quality | [1â€“5/NOT_MEASURED] | [Reference] | [Note] |
| Workflow usability | [1â€“5/NOT_MEASURED] | [Reference] | [Note] |
| Closeout and revocation awareness | [1â€“5/NOT_MEASURED] | [Reference] | [Note] |

## Analyst conclusion

- Independent conclusion: `[Analyst response]`
- Confidence: `[Low / Medium / High / Not stated]`
- Evidence relied upon: `[References]`
- Missing evidence: `[Response]`
- Contradictions: `[Response]`
- Final decision: `[Analyst decision]`

## Advisory comparison

- Advisory material presented: `[Yes/No/Not measured]`
- Analyst accepted, challenged, or rejected it: `[Response]`
- Reason: `[Analyst response]`
- Agreement classification: `[Same evidence / Different reasoning / Correction / Unresolved / Not applicable]`
- Reviewer note: `[Observation]`

## Security and control observations

- Synthetic data only: `[PASS / BLOCKED / NOT_MEASURED]`
- Tenant boundary: `[PASS / BLOCKED / NOT_MEASURED]`
- Privileged/denied actions: `[PASS / BLOCKED / NOT_MEASURED]`
- Audit/provenance: `[PASS / BLOCKED / NOT_MEASURED]`
- Secret-free evidence: `[PASS / BLOCKED / NOT_MEASURED]`
- Access revocation: `[PASS / BLOCKED / NOT_MEASURED]`
- Stop event raised: `[Yes/No]`
- Incident/reference: `[Reference or None]`

## Reviewer disposition

- Evidence sufficient for this scorecard: `[Yes/No/Partially]`
- Items requiring re-test: `[Items]`
- Limitations: `[Limitations]`
- Reviewer sign-off reference: `[Reference]`

