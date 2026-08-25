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
                                  controls + metrics + findings
                                             |
                                  immutable certification report
```

## Evidence sources

The runner aggregates:

- investigation-memory validation;
- organizational cyber-memory validation;
- operational accuracy validation;
- enterprise proof validation;
- controlled operational pilot validation; and
- investigation performance telemetry.

Each source becomes a `CertificationEvidence` record containing its source
version, source report digest, stable replay digest, evidence digest, and
references. Performance report digests may vary because timings are observed;
the certification replay identity uses the source's stable replay/input
digest instead.

## Controls

The report evaluates security, AI-investigation, performance, and operational
controls:

- tenant isolation, authorization, fail-closed behavior, audit integrity, and
  append-only evidence;
- verdict consistency, evidence provenance, confidence calibration, and
  advisory-only memory boundaries;
- latency, scale, and memory overhead; and
- replay stability, deterministic execution, and report integrity.

Required controls appear in `passed_controls` or `failed_controls`. A failed
required control causes the CLI to return a non-zero status. Findings preserve
the related evidence references. Warnings explicitly identify the synthetic
scope and host-observed timing limitations.

## Security boundaries

- `InvestigationCoordinator`, `InvestigationOrchestrator`,
  `RuntimeTaskExecutor`, and `InvestigationResult` are not redesigned.
- Authorization and verdict enforcement remain outside certification authority.
- Memory remains advisory-only; no response action or autonomous decision is
  introduced.
- Tenant boundaries and evidence provenance are inherited from the validated
  source reports.
- Certification report writing is append-only and refuses overwrite.
- The report includes commit SHA, timestamp, environment metadata, validation
  digest, replay digest, report digest, controls, findings, warnings, and
  evidence references.

## Run validation

```text
python scripts/validate_enterprise_certification.py --generated-at 2026-08-25T00:00:00+00:00
python scripts/validate_enterprise_certification.py --output artifacts/enterprise-certification.json
```

The CLI runs certification twice and verifies identical replay digests before
emitting the report. The timestamp and environment metadata are part of the
immutable report content hash but are excluded from replay identity.

This milestone intentionally adds no vector database, external integration,
production deployment, autonomous response, or investigation logic change.
