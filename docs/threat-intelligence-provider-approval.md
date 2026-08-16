# VirusTotal Enterprise/private API approval package

**Phase 107.2A status: APPROVAL PACKAGE — NOT PROVIDER APPROVAL**

`RECOMMENDED` is not `APPROVED`. This package records questions and evidence
requirements for the conditional recommendation in
`threat-intelligence-provider-selection.md`. No account, credential, API key,
endpoint, SDK, or live adapter exists. **Phase 107.3 cannot begin until the
required approvals below are confirmed in writing.**

## Approval scope

The candidate is VirusTotal Enterprise/private API only. VirusTotal public API is
excluded because its published documentation limits it to non-commercial use.
This package requests written confirmation; it does not assert that any answer is
true or that VirusTotal has approved Sentinel DNA.

## Questionnaire and approval matrix

| # | Requirement / provider question | Evidence required | Owner | Status | Blocking? | Decision |
|---:|---|---|---|---|---|---|
| 1 | Commercial SaaS usage | Executed agreement | Commercial | UNKNOWN | Yes | Pending |
| 2 | Multi-tenant/service-bureau rights | Written permission | Commercial | UNKNOWN | Yes | Pending |
| 3 | Customer IOC lookup rights | Contract clause | Legal/Privacy | UNKNOWN | Yes | Pending |
| 4 | API redistribution restrictions | Contract and product terms | Legal | UNKNOWN | Yes | Pending |
| 5 | Derivative-data restrictions | Contract clause | Legal/Product | UNKNOWN | Yes | Pending |
| 6 | Intelligence storage rights | Written retention/license terms | Legal | UNKNOWN | Yes | Pending |
| 7 | Evidence retention rights | Contract clause | Legal/Privacy | UNKNOWN | Yes | Pending |
| 8 | Caching rights | Contract/API terms | Legal/Engineering | UNKNOWN | Yes | Pending |
| 9 | Historical intelligence storage | Contract clause | Legal/Product | UNKNOWN | Yes | Pending |
| 10 | Customer-facing display rights | Display/redistribution permission | Product/Legal | UNKNOWN | Yes | Pending |
| 11 | Internal AI processing rights | Written AI-use permission | Legal/AI | UNKNOWN | Yes | Pending |
| 12 | AI-generated derivative conclusions | Written derivative-use permission | Legal/AI | UNKNOWN | Yes | Pending |
| 13 | Data residency | Processing-region schedule | Privacy | UNKNOWN | Yes | Pending |
| 14 | Data retention | Retention schedule | Privacy | UNKNOWN | Yes | Pending |
| 15 | Data deletion | Deletion SLA and certificate | Privacy | UNKNOWN | Yes | Pending |
| 16 | Subprocessors | Current subprocessor list | Privacy | UNKNOWN | Yes | Pending |
| 17 | DPA availability | Executable DPA | Privacy/Legal | UNKNOWN | Yes | Pending |
| 18 | Security certifications | Current SOC/ISO reports | Security | UNKNOWN | Yes | Pending |
| 19 | Incident notification | Notice SLA and process | Security/Legal | UNKNOWN | Yes | Pending |
| 20 | SLA | Executed service SLA | Procurement | UNKNOWN | Yes | Pending |
| 21 | API availability | SLA/status history | Reliability | UNKNOWN | Yes | Pending |
| 22 | Rate limits | Contracted limits | Engineering | UNKNOWN | Yes | Pending |
| 23 | Quotas | Daily/monthly quota schedule | FinOps | UNKNOWN | Yes | Pending |
| 24 | Burst limits | Burst policy | Engineering | UNKNOWN | Yes | Pending |
| 25 | Credential rotation | Rotation documentation | Security | UNKNOWN | Yes | Pending |
| 26 | API key scope | Scope/least-privilege model | Security | UNKNOWN | Yes | Pending |
| 27 | IP allowlisting | Enterprise capability confirmation | Security | UNKNOWN | No | Pending |
| 28 | Private API endpoint options | Approved endpoint architecture | Security/Network | UNKNOWN | Yes | Pending |
| 29 | Sandbox availability | Isolated test offer | Engineering | UNKNOWN | Yes | Pending |
| 30 | Approved HTTPS hostnames | Signed allowlist | Network/Security | UNKNOWN | Yes | Pending |
| 31 | Supported lookup endpoints | Endpoint inventory | Engineering | UNKNOWN | Yes | Pending |
| 32 | File upload restrictions | Contract and adapter policy | Security | UNKNOWN | Yes | Pending |
| 33 | URL submission restrictions | Contract and adapter policy | Security | UNKNOWN | Yes | Pending |
| 34 | Passive lookup-only operation | Written confirmation and test evidence | Engineering | UNKNOWN | Yes | Pending |
| 35 | Customer IOC disclosure | DPA and customer notice | Privacy/Product | UNKNOWN | Yes | Pending |
| 36 | Confidentiality implications | Threat model and contract | Security/Legal | UNKNOWN | Yes | Pending |
| 37 | Enterprise pricing | Written quote | Procurement/FinOps | UNKNOWN | Yes | Pending |
| 38 | Minimum contract | Order form/term | Procurement | UNKNOWN | Yes | Pending |
| 39 | Usage-based pricing | Rate card | FinOps | UNKNOWN | Yes | Pending |
| 40 | Overage pricing | Overage schedule | FinOps | UNKNOWN | Yes | Pending |
| 41 | Geographic restrictions | Regional-use terms | Legal/Privacy | UNKNOWN | Yes | Pending |
| 42 | Termination implications | Termination clause | Legal | UNKNOWN | Yes | Pending |
| 43 | Export/deletion on termination | Export and deletion procedure | Privacy/Engineering | UNKNOWN | Yes | Pending |
| 44 | Audit rights | Audit/reporting terms | Security/Legal | UNKNOWN | Yes | Pending |
| 45 | Compliance requirements | Provider and Sentinel control mapping | Compliance | UNKNOWN | Yes | Pending |

`APPROVED` may be entered only by the named owner after evidence is attached.
An assumption, public marketing statement, or this document cannot change an
`UNKNOWN` to `CONFIRMED` or `APPROVED`.

## Sentinel DNA security position

The future adapter must be lookup-only, send no malware/files/customer payloads,
perform no arbitrary URL fetching, and derive its destination solely from a
trusted HTTPS allowlist. It must enforce bounded connection/read/total timeouts,
response-size limits, redirect blocking, supported-IOC validation, authenticated
tenant authorization, tenant opt-in, per-tenant quota, audit identity, provider
provenance, secret references only, redacted errors/evidence, and fail-closed
behavior. Provider metadata never establishes tenant or actor authority.

## Data flow and disclosure boundary

```text
Customer IOC
  -> Authenticated Sentinel DNA tenant/actor
  -> Tenant authorization and opt-in policy
  -> ThreatIntelligenceGateway
  -> Future provider adapter
  -> Approved VirusTotal lookup
  -> Normalized intelligence
  -> Provenance and evidence
  -> AI investigation reasoning
```

The only proposed data leaving Sentinel DNA is the selected IOC value, its IOC
type, and strictly necessary lookup metadata. Tenant and actor identifiers remain
Sentinel DNA audit context and are not provider authority. No case narrative,
email body, attachment, document, credential, token, unrelated case data, or
customer payload may leave Sentinel DNA. An IOC itself may be sensitive customer
security information and must be disclosed, controlled, and audited as such.

## Future customer control model (design only)

Customer-facing controls should eventually include external lookup enabled/disabled,
tenant opt-in, allowed IOC types, lookup audit trail, quota, retention policy,
provider disclosure notice, and platform-managed versus customer-owned credential
choice. This phase does not implement those controls.

## Automatic blockers

Any of the following keeps the package unapproved: no commercial SaaS or
multi-tenant authorization; prohibited customer IOC lookup; unacceptable retention,
residency, AI/derivative processing, security terms, pricing, quota, or API
availability; inability to enforce lookup-only behavior; or inability to meet the
existing HTTPS, timeout, response-size, redirect, authorization, provenance, and
secret-handling requirements.

## Phase 107.3 gate

Before implementation begins, owners must attach confirmed evidence for all
blocking rows, execute the commercial agreement and DPA, approve the privacy and
security threat models, identify the exact HTTPS host and lookup endpoints, record
the canonical secret reference, set quota and retention policy, and issue an
explicit production activation decision. Until then: **RECOMMENDED ≠ APPROVED**.
