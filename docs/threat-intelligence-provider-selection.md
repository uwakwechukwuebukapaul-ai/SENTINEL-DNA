# Threat-intelligence provider selection and activation gate

Phase 107.1 does not approve, configure, or contact a provider. A candidate is
only eligible after business, privacy, security, and operations approval.

| Criterion | Evaluation evidence |
| --- | --- |
| IOC coverage | IPv4/IPv6, domain, URL, hash coverage and data quality |
| Intelligence quality | Reputation, malware, actors, campaigns, ATT&CK, history, provenance |
| Operations | API stability, SLA, reliability, rate limits, sandbox support |
| Commercial fit | Cost, enterprise licensing, SaaS redistribution rights |
| Governance | Retention, privacy, residency, security review, auditability |

Candidates such as VirusTotal, AbuseIPDB, AlienVault OTX, MISP, and STIX/TAXII
sources are evaluation candidates only—not approved integrations.

## Activation gate

1. Record a signed provider approval and allowlist the provider ID in deployment configuration.
2. Provide a production HTTPS endpoint and a deployment-managed secret reference.
3. Set `enabled` and the separate `production_enabled` switch explicitly.
4. Inject a bounded transport conforming to `TransportContract`; validate it in an opt-in sandbox test.
5. Register exactly one approved adapter with the existing `ThreatIntelligenceGateway`.

The provider remains an evidence source. Sentinel DNA retains reasoning and all
decision authority; multiple sources may later be compared for provenance,
freshness, and disagreement rather than treated as a verdict API.
