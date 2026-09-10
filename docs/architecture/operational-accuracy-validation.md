# Operational Accuracy Validation Framework

The Sentinel DNA operational accuracy framework evaluates AI Investigator V1
across three controlled modes:

```text
Synthetic SOC Dataset + Analyst Ground Truth
                    |
                    v
          OperationalAccuracyEvaluator
          /          |                \
     Baseline   Investigation      Organizational
                 Memory             Cyber Memory
                    |
                    v
       Accuracy + Quality + Efficiency Metrics
                    |
                    v
          Immutable Validation Report
```

## Dataset and ground truth

The deterministic dataset covers phishing compromise, credential theft, malware
execution, suspicious authentication, lateral movement, command and control,
benign false positives, and multi-IOC investigations. Each scenario is tenant
scoped and stores expected verdict, evidence references, MITRE ATT&CK
techniques, IOC relationships, and analyst confidence.

Each observation keeps `advisory_verdict` separate from `enforced_verdict`.
Memory may improve the advisory evidence and reasoning projection, but the
authoritative enforcement projection is held constant for safety validation.
Disagreement reasons identify missing verdict agreement, evidence, MITRE
mapping, or IOC relationships.

## Metrics

The evaluator calculates:

- verdict agreement, false-positive count/reduction, and false-negative detection
- evidence relevance, MITRE mapping accuracy, and IOC relationship accuracy
- confidence calibration, uncertainty reduction, reasoning completeness,
  provenance coverage, and citation coverage
- execution latency, analyst review-time reduction, repeated-investigation
  reuse, and organizational knowledge reuse rate

The report includes per-mode aggregates, memory benefit score, latency impact,
safety validation, and a replay digest. Timing and review-time fields are
excluded from the replay digest because they are host-dependent.

## Security boundaries

- Tenant identity is required and mixed-tenant datasets are rejected.
- Memory is advisory only and cannot change authorization, verdict enforcement,
  response automation, or fail-closed behavior.
- The canonical `InvestigationCoordinator`, `InvestigationOrchestrator`,
  `RuntimeTaskExecutor`, and `InvestigationResult` contracts are not modified.
- Result schema equality is checked against the canonical envelope.
- Validation reports are frozen models with content digests and are written as
  evidence artifacts; they do not become authoritative policy.

Run the framework with:

```text
python scripts/validate_operational_accuracy.py --output artifacts/operational-accuracy-validation.json
```

## Future evaluation expansion

The dataset can later ingest redacted production replay fixtures and analyst
adjudication batches. Any future AI, vector, or provider-backed retrieval must
feed normalized observations into this same evaluator and preserve the safety
invariants. This enables enterprise quality tracking without turning evaluation
signals into autonomous operational authority.
