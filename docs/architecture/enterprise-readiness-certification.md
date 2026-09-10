# Sentinel DNA Enterprise Readiness Certification

The enterprise readiness certification layer packages previously validated
evidence into one auditable readiness report. It is evidence packaging, not a
new investigation or decision engine.

```text
Investigation Memory validation --------+
Organizational Memory validation ------+\
Operational Accuracy validation -------+ \\n+Enterprise Proof validation -----------+  > Certification Runner
Controlled Operational Pilot -----------+ /       |
Performance telemetry -----------------+/        v
Billing entitlement validation --------+         |
                                  controls + metrics + findings
                                             |
                                  immutable certification report
                                             |
                                  Enterprise Evidence Closure
                                             |
                                  immutable closure artifact
```

## Evidence sources

The runner aggregates:

- investigation-memory validation;
- organizational cyber-memory validation;
- operational accuracy validation;
- enterprise proof validation;
- controlled operational pilot validation; and
- investigation performance telemetry; and
- billing entitlement operational validation.

Billing is a first-class evidence source. Its report contributes five
synthetic lifecycle scenarios, entitlement transitions, access decisions,
audit checks, investigation/evidence preservation checks, provenance checks,
security invariants, and a billing replay digest. Certification retains the
source report digest as an audit reference and uses the billing replay digest
for stable evidence identity.

Each source becomes a `CertificationEvidence` record containing its source
version, source report digest, stable replay digest, evidence digest, and
references. Performance report digests may vary because timings are observed;
the certification replay identity uses the source's stable replay/input
digest instead.

## Enterprise evidence closure

`EnterpriseEvidenceClosureRunner` is the final evidence consolidation layer.
It discovers and normalizes sixteen required evidence sources: certification,
enterprise proof, trust closure, investigation memory, organizational memory,
operational accuracy, controlled pilot, deployment contract, recovery
readiness, billing entitlement validation, runtime readiness, SQLite migration
rehearsal, disposable PostgreSQL rehearsal, backup/restore, operational
ownership, and release hygiene. The closure report records each source's
status, report and replay references, bounded provenance metadata, total
control count, and one deterministic control matrix.

Closure is fail-closed. A missing source, unavailable replay digest, failed
required control, or reported trust/deployment/recovery blocker is retained in
`remaining_blockers` and makes `closure_result` `blocked`. The layer does not
turn a passing validation into deployment authorization; it consolidates proof
for an independently governed release decision.

The replay digest includes only stable source replay identities, normalized
control results, and blocker identifiers. Timestamps, commit metadata, report
digests, host paths, and observed timing are excluded from replay identity.
The artifact digest covers the report content excluding the digest field itself
and is retained for immutable artifact verification.

## Controls

The report evaluates security, AI-investigation, performance, and operational
controls:

- tenant isolation, authorization, fail-closed behavior, audit integrity, and
  append-only evidence;
- verdict consistency, evidence provenance, confidence calibration, and
  advisory-only memory boundaries;
- latency, scale, and memory overhead; and
- replay stability, deterministic execution, and report integrity.

Billing-specific required controls are unpaid tenant safety, entitlement
transition correctness, upgrade preservation, downgrade safety, investigation
preservation, billing failure fail-closed behavior, and billing audit
continuity.

Required controls appear in `passed_controls` or `failed_controls`. A failed
required control causes the CLI to return a non-zero status. Findings preserve
the related evidence references. Warnings explicitly identify the synthetic
scope and host-observed timing limitations.

The release assurance workflow is:

1. Run each source validator in its evidence-only boundary.
2. Run enterprise certification and enterprise proof aggregation.
3. Run `validate_enterprise_evidence_closure.py` to verify source presence,
   replay references, control results, and blockers.
4. Store the dated closure artifact append-only.
5. Resolve remaining operational gates through separately authorized release
   governance. Closure itself performs no deployment or external operation.

## Security boundaries

- `InvestigationCoordinator`, `InvestigationOrchestrator`,
  `RuntimeTaskExecutor`, and `InvestigationResult` are not redesigned.
- Authorization and verdict enforcement remain outside certification authority.
- Memory remains advisory-only; no response action or autonomous decision is
  introduced.
- Tenant boundaries and evidence provenance are inherited from the validated
  source reports.
- Billing state is validated as an entitlement-only transition. Identity,
  tenant ownership, investigation history, evidence provenance, authorization,
  verdict enforcement, and autonomous response boundaries remain outside the
  billing evidence layer.
- Billing validation uses disposable synthetic SQLite state and a synthetic
  billing provider marker. It performs no real payment-provider calls, payment
  processing, credential change, or production billing operation.
- Certification report writing is append-only and refuses overwrite.
- The report includes commit SHA, timestamp, environment metadata, validation
  digest, replay digest, report digest, controls, findings, warnings, and
  evidence references.

## Run validation

```text
python scripts/validate_enterprise_certification.py --generated-at 2026-08-25T00:00:00+00:00
python scripts/validate_enterprise_certification.py --output artifacts/enterprise-certification.json
python scripts/validate_enterprise_certification.py --output artifacts/enterprise-certification-billing-refresh-2026-08-25.json --generated-at 2026-08-25T00:00:00+00:00
python scripts/validate_enterprise_evidence_closure.py --output artifacts/enterprise-evidence-closure-2026-08-25.json --generated-at 2026-08-25T00:00:00+00:00
```

The CLI runs certification twice and verifies identical replay digests before
emitting the report. The timestamp and environment metadata are part of the
immutable report content hash but are excluded from replay identity.

This milestone intentionally adds no vector database, external integration,
production deployment, autonomous response, or investigation logic change.
Production payment operations remain out of scope for certification evidence
and require a separate controlled operational process.
