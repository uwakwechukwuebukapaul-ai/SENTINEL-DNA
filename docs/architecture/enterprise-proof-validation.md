# Enterprise Proof Validation Layer

The enterprise proof layer packages the post-accuracy trust checks needed for
enterprise validation. It is an offline, deterministic evidence generator. It
does not execute production investigations, alter authorization, or make
autonomous decisions.

```text
                    Synthetic tenant A / tenant B environments
                                      |
          +---------------------------+--------------------------+
          |                           |                          |
 Tenant isolation              SOC analyst                 Investigation scale
 certification                 effectiveness                benchmark
          |                           |                          |
          +---------------------------+--------------------------+
                                      v
                         EnterpriseProofReportGenerator
                                      |
              immutable digest + replay digest + safety invariants
```

## Proof domains

Tenant certification exercises same-tenant reads and cross-tenant reads for
investigation memory and organizational memory. Cross-tenant attempts must be
denied with no observed resource or provenance. Same-tenant observations must
retain tenant and source-investigation provenance.

The analyst benchmark compares the baseline and organizational-memory arms of
the deterministic SOC dataset. It measures review time, analyst confidence,
AI recommendation acceptance, false escalations, and provenance retention.

The scale benchmark produces deterministic simulations at 10, 100, and 1000
investigations. It reports p50/p95 timing and memory overhead for baseline and
memory-enhanced execution. Its timing model is explicitly synthetic and does
not use host wall-clock measurements or external providers; this makes replay
digests stable. Production performance certification remains a separate
deployment exercise.

## Security boundaries

- `InvestigationCoordinator`, `InvestigationOrchestrator`,
  `RuntimeTaskExecutor`, and `InvestigationResult` contracts remain unchanged.
- Authorization and verdict enforcement remain authoritative and are checked
  against the operational accuracy safety projection.
- Memory is advisory-only. Proof output cannot approve, block, escalate, or
  automate a response.
- Tenant A/B data is synthetic and disjoint. Cross-tenant access is fail-closed.
- Evidence provenance is checked for tenant identity, source, and observed
  investigation context.
- Reports are frozen models with a content digest. The writer refuses to
  overwrite an existing report path, preserving append-only evidence handling.

## Report and replay

Run:

```text
python scripts/validate_enterprise_proof.py --output artifacts/enterprise-proof-validation.json
```

The report contains the architecture summary, certification attempts, analyst
benchmark cases, scale points, safety validation, replay digest, and report
digest. Re-running the same fixture set produces the same replay digest;
`generated_at` is excluded from replay identity but included in the report
content hash. The report explicitly records deterministic replay and append-only
evidence invariants.

## Enterprise value

This layer supplies an auditable trust package around investigation quality:
isolation evidence demonstrates tenant custody, analyst outcomes demonstrate
operational usefulness, and scale estimates expose cost before production
rollout. Future provider-backed or production-replay evidence can implement
the same normalized models without widening decision authority.
