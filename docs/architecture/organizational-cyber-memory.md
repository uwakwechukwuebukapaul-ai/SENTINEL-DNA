# Organizational Cyber Memory Foundation

Sentinel DNA organizational memory turns validated investigation history into
tenant-scoped, reusable evidence context. It is an additive advisory layer
around the canonical investigation path.

## Architecture

```text
InvestigationCoordinator
        |
        +--> InvestigationMemoryService
        |       +--> completed investigation evidence
        |       +--> analyst feedback
        |
        +--> OrganizationalMemoryService
                +--> DeterministicSimilarityProvider
                +--> OrganizationalMemoryConsolidator
                +--> OrganizationalMemoryRepository
                        +--> organizational_memory
                        +--> organizational_memory_audit (append-only)
```

The canonical `InvestigationOrchestrator`, `RuntimeTaskExecutor`, and
`InvestigationResult` contracts remain unchanged. Organizational context is
attached only as advisory metadata/intelligence context.

## Data flow

1. A completed, tenant-scoped investigation is already stored in the existing
   investigation memory boundary.
2. The consolidator accepts only validated findings, MITRE mappings, IOC
   relationships, and analyst feedback.
3. It deterministically emits `InvestigationPattern`,
   `AttackCampaignMemory`, `AnalystKnowledgeEntry`, `DetectionLearningRecord`,
   and `ResponsePlaybookMemory` records when their evidence inputs exist.
4. Each record preserves why it was stored, the source investigation, evidence
   references/fingerprint, attribution, confidence, observation time, and an
   immutable audit hash.
5. Future investigations retrieve same-tenant records through the
   provider-neutral similarity interface. The resulting context is advisory
   and cannot alter verdict, authorization, response automation, or fail-closed
   controls.
6. Analyst review remains the feedback loop: completed investigation → analyst
   feedback → knowledge extraction → future advisory context.

## Security boundaries

- Every organizational read and write requires an explicit tenant ID.
- Cross-tenant source investigations are rejected.
- Unvalidated source memory is blocked from consolidation.
- Evidence provenance is retained; raw provider payloads are not copied into
  organizational memory.
- Domain records are persisted append-only, with SQLite update/delete triggers
  and content hashes.
- Similarity is deterministic Jaccard scoring only; it has no authority over
  decisions.
- Consolidation and retrieval failures are advisory failures and do not make
  an investigation authorize work or change a verdict.

## Validation

Run the organizational validation suite:

```text
python scripts/validate_organizational_memory.py --output artifacts/organizational-memory-validation.json
```

The suite compares memory-disabled and memory-enabled synthetic investigations
and verifies additional organizational context, verdict invariance,
authorization invariance, tenant isolation, provenance, replay digest stability,
and observed latency impact.

## Future expansion

`MemorySimilarityProvider` is the extension boundary for a future vector index,
embedding provider, graph correlation store, or enterprise provider adapter.
Those systems may improve retrieval ranking, but must normalize to the same
provenance-bearing records and preserve the advisory-only contract. Autonomous
verdict changes, response automation, and authorization decisions remain out of
scope for this layer.

## Enterprise value

This foundation gives SOC teams durable organizational recall: recurring
phishing infrastructure, repeated attacker behavior, effective detections,
analyst resolution patterns, and validated response playbooks become searchable
across future investigations without treating historical data as unquestioned
truth. Evidence provenance and human validation remain the basis for reuse.
