# FAVP Analyst Workflow

The analyst remains the final decision maker throughout validation.

1. Open the assigned synthetic scenario and review its objectives, MITRE
   ATT&CK mapping, difficulty, and evidence references.
2. Execute the investigation using the bounded Sentinel DNA workspace.
3. Review the AI investigation output as advisory material only.
4. Record an independent `analyst_decision`; never copy an AI recommendation
   into the decision field without analyst review.
5. Record evidence references by SHA-256 and provenance references. Raw event
   content is not accepted by the FAVP repository.
6. Record features used, elapsed time, uncertainty, incorrect reasoning, and
   limitations.
7. Score trust, reasoning understanding, confidence, provenance, timeline,
   IOC enrichment, and evidence quality from 1 to 5.
8. Provide optional payment-signal feedback: interest, requested tier,
   integrations, and deployment requirements.

The workspace exposes `ai_boundary: advisory_only` and
`synthetic_only: true`. It has no credential controls, production connectors,
browser automation, autonomous action, or destructive operation.
