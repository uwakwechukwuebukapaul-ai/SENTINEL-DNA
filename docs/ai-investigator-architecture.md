# AI Investigator architecture

Sentinel DNA keeps one investigation engine: `InvestigationCoordinator` delegates to `InvestigationOrchestrator`, `RuntimeTaskExecutor`, durable execution repositories, `InvestigationResult`, and tenant-scoped read models. Explainability, graph, quality, report, and analyst workflow projections are versioned views over canonical data.

AI output is bounded by evidence provenance, provider observations, confidence decomposition, contradictions, freshness, availability, and uncertainty semantics. The system distinguishes insufficient evidence, provider unavailable, provider disagreement, stale intelligence, contradictory evidence, and low confidence. Recommendations remain advisory-only.

Evidence and provider responses are untrusted content. They cannot change system instructions, authorization, workflow state, or destructive action policy. Analysts review and approve governed outcomes through auditable append-only actions.
