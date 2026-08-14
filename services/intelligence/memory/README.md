# Investigation intelligence memory

This package stores validated, structured SOC investigation intelligence: outcomes, evidence references, reasoning summaries, risk, confidence, and MITRE techniques. It is deliberately separate from the AI runtime: memory is a persistence and retrieval boundary, not chat history, model training, or automatic learning from untrusted evidence.

The current deterministic SQLite repository can later be replaced or supplemented by a vector index for semantic retrieval. A future enterprise knowledge graph can connect cases, entities, evidence, techniques, and recurring attack patterns while retaining this service boundary and synthetic-only safeguards.
