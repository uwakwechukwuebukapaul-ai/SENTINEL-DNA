# Intelligence layers

## Investigation Decision Intelligence

The `investigation_decision` package is a tenant-scoped, read-only advisory layer. It composes existing investigation context and intelligence outputs to interpret evidence strength, uncertainty, contributing factors, and investigation path considerations.

It does not load evidence independently, replace `InvestigationContext`, execute decisions, modify investigations, or trigger response actions. The AI SOC Copilot can present its advisory output, while lifecycle intelligence supplies complementary progress visibility; neither relationship changes ownership of investigation orchestration.

Outputs distinguish available evidence from derived interpretation, retain provenance, and use explicit insufficient-evidence states. No causal or certainty claims are made.
