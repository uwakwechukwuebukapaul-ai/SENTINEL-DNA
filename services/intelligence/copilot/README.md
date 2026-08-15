# SOC analyst copilot

The copilot is an advisory presentation and question-answering layer over completed investigation intelligence. It explains and summarizes evidence, answers analyst questions, and recommends next steps without executing actions or mutating context.

It differs from the EvidenceReasoner: reasoning derives evidence-grounded findings, while the copilot translates those findings, decisions, and historical references into analyst-facing context. Future extensions include conversational and voice SOC assistance, multi-case search, threat hunting support, and executive reporting.
The investigation Copilot is an evidence-grounded, tenant-scoped interpretation layer over existing workspace and intelligence outputs. Responses separate observed evidence, derived reasoning, uncertainty, recommendations, confidence, provenance, and required human review. It does not replace investigation orchestration, evidence, threat, risk, compliance, governance, or workspace ownership; it performs no execution or source mutation.

Provider integration is abstracted by `CopilotProvider`. The default provider is deterministic and local; hosted or local model adapters may be added later without changing the service contract. TTS is an optional presentation capability and is not required for Sentinel DNA investigations or Copilot operation.
