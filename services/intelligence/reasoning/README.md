# Evidence-grounded reasoning

`EvidenceReasoner` is a deterministic, offline-safe reasoning subsystem. It consumes the canonical investigation context (evidence, IOCs, timeline, enrichment, and plan), emits serializable findings, and never mutates context or executes actions.

When an existing `AIRuntimeService` is supplied, it receives a structured investigation prompt. AI output is advisory metadata only; deterministic findings remain evidence-linked and synthetic-safe.
