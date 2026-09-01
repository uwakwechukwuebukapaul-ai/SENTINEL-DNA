# Commercial Metrics Dashboard

## Governance

The dashboard is a measurement schema, not a set of results. Every populated value requires a source, owner, period, definition, and quality note. Empty values are preferable to invented values.

## Pipeline KPIs

| KPI | Definition | Minimum fields |
|---|---|---|
| Contacted analysts | Analysts receiving an approved outreach touch in the period | Analyst record, date, channel, consent/status |
| Accepted analysts | Analysts accepting the FAVP or design-partner invitation | Acceptance reference, date |
| Design partners | Organizations with an approved active design-partner record | Organization, stage, owner, start/end |
| Paid pilots | Customers with a signed paid pilot order form in the period | Order reference, package, fee status, start/end |
| Customers | Customers with an active annual subscription | Subscription reference, start/end |

## Product KPIs

| KPI | Definition | Required guardrail |
|---|---|---|
| Investigations completed | Approved investigations reaching the agreed review state | Include denominator and workflow scope |
| Evidence generated | Evidence records created under the approved scope | Count records, not unsupported impact |
| Analyst satisfaction | Survey result for a defined cohort and period | Report response count and scale |
| Blocked workflows | Attempts blocked by control, data, product, or process | Categorize cause and severity |

## Business KPIs

| KPI | Definition | Required guardrail |
|---|---|---|
| Pilot conversion rate | Defined paid-pilot conversions divided by the stated eligible cohort | State cohort, period, and denominator |
| Annual contract value | Contracted recurring value under executed subscription terms | Use booked/contracted status; do not mix forecast |
| Retention | Customers renewed under a defined cohort and period | Define logo/revenue basis and exclusions |
| Expansion revenue | Executed incremental recurring value from existing customers | Require order-form evidence |

## Dashboard record schema

```text
metric_id: [stable identifier]
period: [UTC start/end]
value: [number or null]
unit: [count, rate, currency, score]
cohort: [definition]
numerator: [if applicable]
denominator: [if applicable]
source_reference: [system/report reference]
owner: [named owner]
quality_status: [verified|provisional|not_measured]
limitations: [plain-language note]
approved_for_external_use: [yes|no]
```

## Reporting cadence

- Weekly: operational pipeline, product blockers, access and evidence exceptions.
- Monthly: scorecards, stage movement, procurement blockers, and support load.
- At closeout: pilot conversion and customer decision, with denominator.
- Quarterly: retention and expansion only from executed commercial records.

## Forecast governance

Conversion probability is an internal planning hypothesis, not a KPI result. It must be based on named evidence and an explicit methodology. Do not publish pipeline value as revenue, convert qualitative enthusiasm into a percentage, or use customer proof without approval.
