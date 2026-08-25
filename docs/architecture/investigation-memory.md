# Investigation Memory and Organizational Learning

Sentinel DNA investigation memory is an additive, advisory intelligence layer
around the canonical `InvestigationCoordinator` → `InvestigationOrchestrator` →
`RuntimeTaskExecutor` path. It does not replace or mutate those contracts, and
it never authorizes a response or changes a verdict by itself.

## Flow

1. A tenant-scoped investigation is normalized with its evidence references.
2. `MemoryService.build_learning_context()` retrieves historical records from
   the same tenant and scores deterministic attack-pattern similarity.
3. The context is attached to `InvestigationResult.intelligence` and metadata
   as an advisory learning signal.
4. The completed result is persisted with evidence fingerprints, provenance,
   verdict, confidence, and a deterministic memory ID.
5. Analyst feedback is stored as an append-only memory event and remains linked
   to the tenant, investigation, analyst, and evidence references.

## Security and replay properties

- Every memory read includes a tenant predicate; missing tenant context fails
  closed for learning reads.
- Repository and feedback records preserve evidence references and provenance,
  while raw evidence is not copied into the memory index.
- Memory IDs and similarity ordering are deterministic for replay and testing.
- Memory and feedback writes append an audit record with a content hash.
- Historical comparison and confidence signals are explicitly `advisory_only`;
  they cannot bypass execution, authorization, or response gates.

## Storage

Migration `007_investigation_memory.py` creates the memory, feedback, and audit
tables. `InvestigationMemoryRepository` also performs additive compatibility
for databases created by the original in-memory-shaped repository. The
provider-neutral service boundary can later be backed by PostgreSQL, a vector
index, or a graph store without changing investigation result contracts.

Future provider adapters (GitLab CI, Jenkins, Azure DevOps, and enterprise
GitHub) should normalize into the same provenance-bearing memory record rather
than writing provider-specific fields into orchestration code.

## Operational validation

`OperationalCyberMemoryValidator` provides an offline, synthetic validation
suite for organizational learning. Run it with:

```text
python scripts/validate_investigation_memory.py --output artifacts/memory-validation.json
```

Each scenario is executed twice: once with an empty memory repository and once
with a deterministic historical case plus analyst feedback preloaded. The
report measures advisory confidence uplift, evidence-reference correlation,
feedback reuse, historical similarity, and observed execution-time delta.

The validator constructs the canonical `InvestigationResult` envelope in both
arms and asserts that its schema, verdict, authorization projection, and
fail-closed state are unchanged. Memory is never consulted for authorization or
verdict enforcement. The report includes tenant and evidence provenance,
historical memory IDs, control-invariant results, an audit trail, and a replay
digest. Timing is retained as observed performance evidence but excluded from
the deterministic digest; replay quality is therefore not dependent on host
load.

This is a validation harness, not an autonomous investigator. It uses no vector
database, embeddings, or external provider calls. Future milestones can add
provider-normalized fixtures and statistical evaluation while retaining these
control assertions.
