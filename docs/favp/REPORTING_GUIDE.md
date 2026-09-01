# FAVP Reporting Guide

The report generator emits a `FAVP Validation Report` with:

- Executive Summary
- Program Scope
- Participant Summary
- Scenario Coverage
- Analyst Feedback Summary
- Evidence Quality Assessment
- AI Boundary Findings
- Security Controls Tested
- Limitations
- Commercial Signals
- Next Recommendations

KPI values are computed only from tenant-scoped records. Program metrics cover
applicants, accepted analysts, active participants, completed validations, and
state counts. Product metrics cover completed investigations, satisfaction,
evidence usefulness, trust, false-positive feedback, and limitation findings.
Commercial metrics cover design-partner candidate state, payment-interest
signals, requested integrations, and requested tiers.

Scores are retained on their source feedback records and aggregated without
inventing a score when there is no feedback. The report is an internal
validation artifact, not a customer case study or certification. A program
owner must review limitations, provenance, revocation, and AI advisory-only
boundaries before any design-partner discussion.

Execution-readiness reports keep observed evidence, analyst feedback, system
measurements, commercial signals, limitations, and future improvements in
separate sections. The final report is a template until those sections are
populated from recorded synthetic validation activity; `insufficient_data` is
not converted into a positive result.
