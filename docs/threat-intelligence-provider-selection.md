# Threat-intelligence provider selection and approval record

**Phase:** 107.2 — due diligence only (2026-08-16)
**Status:** **RECOMMENDED, NOT FORMALLY APPROVED**
**No provider is configured, registered, contacted, or entitled to receive a Sentinel DNA customer IOC through this decision.**

## Sentinel DNA requirements

The first source must fit the existing `ThreatIntelligenceProvider` contract: bounded, authenticated lookup through `ThreatIntelligenceGateway`; normalized observations with provider record, scores, timestamps, status, errors, and source provenance; and no ability to alter tenant identity, evidence ownership, verdict, risk, confidence, or case status. Required coverage is IP, domain, URL, and MD5/SHA-1/SHA-256 lookup; HTTPS-only bounded transport; secret-reference credentials; rate-limit observability; and evidence-quality provenance.

The gateway treats a provider as one evidence source. Sentinel DNA owns reasoning, source disagreement, freshness assessment, tenant authorization, and decisions.

## Candidates considered

| Candidate | Scope and technical fit | Due-diligence outcome |
| --- | --- | --- |
| **VirusTotal Enterprise / private API** | IP, domain, URL, file-hash reports, rich relationships, detection context, sandbox and ATT&CK-related data in private services. | **Recommended conditionally** |
| AbuseIPDB paid / enterprise | IPv4/IPv6 reputation and reports; useful, narrow IP signal. | Not sufficient as first general IOC provider |
| AlienVault OTX | Community pulse/IOC intelligence across common IOC types. | Not recommended; commercial and retention restrictions are disqualifying until negotiated |
| MISP | Self-hosted/share-community platform with rich objects, galaxies, taxonomies, and relationships. | Strategic future fusion candidate, not an external first lookup provider |
| STIX/TAXII 2.1 sources | Standard transport/format for feeds and collections, not a provider or intelligence corpus itself. | Future ingestion interface, not selectable as the first provider |

### Evidence consulted (documentation only; no APIs invoked)

- VirusTotal documents API v3 as JSON/REST and reports for files, URLs, domains, and IPs, with deeper relationships and context in private services: [API overview](https://docs.virustotal.com/reference/overview), [v2-to-v3 guide](https://docs.virustotal.com/reference/api-v2-v3-migration-guide).
- VirusTotal states public API is non-commercial/free-to-consumer use only; private API is for commercial/government use, with custom quotas and usage-based pricing: [public vs. private API](https://docs.virustotal.com/docs/difference-public-private).
- AbuseIPDB documents IPv4/IPv6 checks, confidence score, and report history: [API v2 documentation](https://docs.abuseipdb.com/). Its paid plans publish daily IP query limits; enterprise pricing is custom: [pricing](https://www.abuseipdb.com/pricing). Its terms prohibit resale or exploitation of API/data without express permission: [terms](https://www.abuseipdb.com/legal.html).
- OTX's end-user agreement says it is free for non-commercial end users, prohibits commercial exploitation/service-bureau use, and says submitted user content may be retained, used, and distributed at the provider's discretion: [OTX agreement](https://www.levelblue.com/legal/otx-eula-terms).
- MISP provides an OpenAPI-described ecosystem and documents MISP core as AGPL; taxonomies and galaxies have different, more permissive licenses: [documentation](https://www.misp-project.org/documentation/), [license overview](https://www.misp-project.org/license/).
- TAXII 2.1 is a RESTful CTI exchange protocol over HTTPS with collections and authorization semantics; it is not an intelligence vendor: [OASIS TAXII 2.1](https://docs.oasis-open.org/cti/taxii/v2.1/os/taxii-v2.1-os.html).

## Technical and security comparison

| Dimension | VirusTotal Enterprise | AbuseIPDB paid/enterprise | OTX | MISP | TAXII source |
| --- | --- | --- | --- | --- | --- |
| IP/domain/URL/hash coverage | Strong across all required classes | IP only | Mixed IOC/pulse coverage | Depends on feeds/community | Depends on source |
| Scores, malware, relationships | Strong; private services add rich context | IP confidence/report-centric | Community pulse-centric | Strong modelling; feed dependent | Source dependent |
| ATT&CK/actors/campaigns | Available in richer private intelligence context | Limited/not primary | Some pulse context | Strong galaxies/objects where present | Source dependent |
| API/normalization fit | Good REST/JSON; vendor parser required | Simple REST/JSON; narrow schema | API maturity/stability requires confirmation | Operationally heavy; no managed corpus implied | Standardized STIX, but data quality varies |
| Scaling/rate limits | Private quota is custom; monitor group quota | Published daily tiers; enterprise data feed exists | **UNKNOWN** official enterprise limit/SLA | Self-operated capacity and feed licenses | Per source/contract |
| Credential model | Private service credentials; rotation process **UNKNOWN** | API key, documented regeneration | API key/account model | Self-hosted/operator controlled | Source-specific |

All external lookups can disclose an IOC to a third party. An IOC can reveal a customer domain, IP, URL path, incident timing, or security investigation. The initial adapter must use lookup-only endpoints, prohibit submission/reporting, capture consent/policy context, and give tenants a disable-by-default external-lookup control. No customer IOC may be sent until a data-processing review accepts the provider's retention, onward-use, residency, subprocessor, breach-notice, and deletion terms.

## Commercial, SaaS, and multi-tenant analysis

VirusTotal public API is **disqualified** because its published terms prohibit commercial products/services. The candidate is only the paid private/Enterprise service. Exact SaaS redistribution, service-bureau, derivative-data, retention, regional-processing, and termination rights are **UNKNOWN / REQUIRES COMMERCIAL CONFIRMATION**.

AbuseIPDB paid plans publish 10,000 and 50,000 IP checks/reports per day for Basic and Premium, while enterprise pricing is custom. Its published no-resale language requires express written permission before exposing data to Sentinel DNA tenants. OTX's stated non-commercial/no-service-bureau terms are a critical red flag. MISP licensing permits API use without imposing its AGPL on separate software, but deployment, feed-data rights, operations, and sharing-policy governance remain Sentinel DNA responsibilities. TAXII does not grant rights to any particular feed's data.

**Recommended initial credential model:** one platform-managed enterprise credential in the canonical secret provider, never visible to tenants, with tenant policy opt-in, audit identity, per-tenant quotas, and a future path for customer-owned credentials. This is architectural guidance only; it does not authorize a credential or live integration.

## Unit economics and capacity planning

Planning assumption only: **five deduplicated external lookups per investigation**. Actual IOC fan-out, cache hit rate, endpoint-specific quota weights, agreement price, and tenant mix are **UNKNOWN**.

| Investigation volume | Estimated lookups/day | Approx. lookups/30-day month | Implication |
| --- | ---: | ---: | --- |
| 100/day | 500 | 15,000 | Public VirusTotal remains prohibited; paid quota required |
| 1,000/day | 5,000 | 150,000 | Requires contracted quota and tenant fairness controls |
| 10,000/day | 50,000 | 1,500,000 | Requires enterprise commitment, caching, and hard budget limits |

No price is estimated: VirusTotal private/Enterprise pricing is documented as usage-dependent/contact-sales. AbuseIPDB publishes lower-tier list prices but is not recommended as the first general IOC provider; enterprise pricing is unknown.

## Weighted scorecard

Scores are evidence-based planning judgments, not commercial approval. A critical red flag overrides a numerical total.

| Candidate | Technical 20% | Security/privacy 20% | Commercial/licensing 20% | Enterprise 15% | Economics 10% | Architecture 10% | Strategy 5% | Total /10 | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| VirusTotal Enterprise/private | 9 | 6 | 5 | 8 | 5 | 9 | 8 | **7.2** | Conditional only |
| AbuseIPDB paid/enterprise | 4 | 6 | 5 | 6 | 7 | 7 | 4 | **5.4** | Narrow IP complement |
| OTX | 5 | 2 | 1 | 3 | 8 | 5 | 4 | **3.5** | Critical commercial/privacy red flags |
| MISP | 7 | 7 | 6 | 6 | 5 | 6 | 8 | **6.5** | Future self-hosted fusion path |
| STIX/TAXII source | 5 | 6 | 4 | 6 | 6 | 8 | 7 | **5.6** | Protocol, not provider |

## Recommendation and approval boundary

### Recommended provider: VirusTotal Enterprise / private API — conditional

**Reason:** it best satisfies Sentinel DNA's first-source need for broad IOC coverage, normalized evidence, deep file/URL/domain/IP context, relationships, provenance potential, and future investigation/hunting enrichment. It is not selected for API convenience; its rich context supports evidence-backed investigation reasoning while Sentinel DNA remains the decision-maker.

**Weaknesses and risks:** high/unknown enterprise economics; group quota sharing; third-party IOC disclosure; private-service legal terms; and uncertain SaaS, redistribution, retention, residency, and data-processing rights. Public API use is expressly prohibited for this product. This recommendation does **not** constitute formal approval.

### Alternatives rejected for the first integration

- **AbuseIPDB:** valuable future IP-only secondary source, but inadequate coverage and enrichment depth for the initial general IOC provider.
- **OTX:** published non-commercial/no-service-bureau and user-content retention/distribution terms are incompatible with a multi-tenant commercial default.
- **MISP:** strong strategic internal/fusion option, but a platform requiring operational ownership and feed licensing, not a ready managed first provider.
- **STIX/TAXII:** a transport/interoperability standard; a separately approved intelligence source is still required.

### Required before Phase 107.3 (formal approval gate)

1. Written selection of **VirusTotal Enterprise/private API** and approved environment; explicitly prohibit public API.
2. Approved HTTPS base host, lookup-only operations, IOC types, features, budgets, quota policy, and no-submit/no-upload policy.
3. Canonical secret-reference name and rotation/incident process—no secret value in source, tests, or configuration.
4. Executed agreement explicitly permitting Sentinel DNA's commercial SaaS, multi-tenant, service-bureau/redistribution, derivative-data, and retention use; price, quota, SLA, and termination terms accepted.
5. Privacy/DPA approval of IOC disclosure, retention/onward use, regional processing, subprocessors, legal basis, and customer control.
6. Product approval for tenant opt-in/opt-out, audit record, platform credential governance, rate-limit fairness, and explicit production activation.
7. Security approval of bounded HTTPS transport, logging redaction, allowlisted host, sandbox plan, and adapter threat model.

Until every gate is satisfied, the correct state remains **RECOMMENDED, NOT APPROVED** and no live provider adapter may be implemented.
