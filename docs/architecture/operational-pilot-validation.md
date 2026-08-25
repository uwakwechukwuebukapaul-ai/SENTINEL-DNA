# Controlled Operational Pilot Validation

The operational pilot converts enterprise proof into bounded operational
evidence. It runs synthetic alerts for tenants A, B, and C through a
deterministic execution adapter that consumes the existing normalized
investigation evaluation fixtures. It does not replace or modify the
production investigation path.

```text
Tenant A/B/C synthetic alerts
             |
             v
       Alert ingestion
             |
  Coordinator / Orchestrator contract projection
             |
  Evidence -> IOC -> MITRE -> memory -> reasoning -> report
             |             |
             |             +--> advisory investigation + organizational context
             +--> provenance events + analyst feedback
             |
       Immutable pilot report
       metrics + audit hashes + replay digest + safety checks
```

## Controlled execution

The pilot supports synthetic alert ingestion, bounded investigation execution,
evidence collection, investigation-memory and organizational-memory usage
tracking, analyst feedback capture, and replay verification. One controlled
synthetic evidence-provider failure is included so successful and failed
investigation metrics are both exercised. Failed execution terminates without
an enforced verdict and remains fail-closed.

The timing model is deterministic synthetic timing, not host wall-clock
measurement. This makes repeated pilot runs comparable and keeps the replay
digest stable. Deployment-level performance testing remains a separate step.

## Operational metrics

Reports include completed, successful, and failed investigations; mean/p50/p95
investigation latency; mean evidence retrieval, IOC enrichment, MITRE mapping,
memory retrieval, organizational-memory retrieval, and report-generation
timings; memory item counts; context reuse rate; and analyst feedback count.

## Evidence and security boundaries

- Every alert, evidence item, memory observation, feedback record, and audit
  event carries tenant and investigation scope.
- Provenance events form a hash chain. Each event records its previous hash and
  its own audit hash; report-level execution records form a second chain.
- Cross-tenant data is never used by a pilot execution. Tenant leakage and
  provenance mismatches fail validation.
- `InvestigationResult` keys are compared with the canonical result envelope.
- Authorization status, fail-closed behavior, and enforced verdict remain
  unchanged across memory use.
- Memory is advisory-only and no autonomous response action is executed.
- Report writes are append-only: an existing output path is rejected rather
  than overwritten.

## Run and replay

```text
python scripts/run_operational_pilot.py --generated-at 2026-08-25T00:00:00+00:00
python scripts/run_operational_pilot.py --output artifacts/operational-pilot.json
```

The CLI executes the pilot twice and refuses success if the replay digests
differ. The report includes an immutable content digest, while the replay
digest excludes issuance time so repeated validation of the same fixtures is
stable.

## Future controlled expansion

Production replay adapters may later feed redacted alert and analyst-review
records into `PilotAlert` and the normalized evaluator. Any such adapter must
retain tenant scope, provenance, append-only evidence, and the same
authorization/verdict safety invariants. No vector store, embedding model, or
autonomous response path is required for this milestone.
