# Sentinel DNA Commercial Readiness Blueprint

## Purpose and boundary

This is a product and commercial planning document for Sentinel DNA. It does
not authorize deployment, production configuration, production metadata
changes, image publication, or Gate 1. Commercialization must be additive to
the frozen release and must preserve the existing release and deployment
controls.

Current release identity:

| Artifact | Certified identity |
| --- | --- |
| Git SHA | `8eef9afd588a1dda80975bb997e4baae06a1d06d` |
| Git tree | `6ca1c289586f84e93d5e9bb29fa4490f3dfbae9a` |
| Image ID | **NOT MEASURED FOR THIS COMMIT** |
| Release posture | Engineering complete; image certification external; production blocked |

## 1. Product positioning

### Category

Sentinel DNA should be positioned as an **evidence-first AI SOC
investigation and decision-intelligence platform**. It is an investigation
layer that turns alerts and collected evidence into a traceable investigation,
decision, and analyst action. It is not a generic SIEM replacement and should
not compete primarily on log-ingestion breadth.

The product promise is:

> Help an analyst reach a defensible security decision faster, with every
> material conclusion tied to evidence, provenance, reasoning, and replayable
> execution.

### Strategic contrast

The following is positioning guidance, not a benchmark or a claim that any
competitor lacks the listed capabilities. The major platforms generally have
stronger installed-base reach, telemetry, detection, endpoint, or cloud
security depth. Sentinel DNA should win the investigation and decision layer
where customers want a transparent, provider-neutral AI workflow.

| Platform | Strategic strength customers may already buy | Sentinel DNA position |
| --- | --- | --- |
| Microsoft Sentinel | Broad cloud/security operations ecosystem and SIEM workflow | Investigation acceleration and evidence traceability across existing tools |
| Splunk Enterprise Security | Mature search, detection, and enterprise operations footprint | Replayable AI investigation with explicit evidence-to-decision lineage |
| CrowdStrike Falcon | Strong endpoint-centric security operations and response posture | Provider-neutral investigation reasoning across endpoint and external evidence |
| Google SecOps | Large-scale security analytics and intelligence-oriented operations | Analyst decision intelligence with a human-reviewable investigation record |
| Elastic Security | Flexible search, analytics, and extensible security data workflows | A focused AI investigation experience over the customer's existing evidence |
| Cortex XDR | Integrated endpoint, network, and response workflows | Portable investigation orchestration and provenance across multiple providers |

Sentinel DNA should integrate with these ecosystems where practical rather
than ask customers to replace them on day one.

## 2. Ideal customer profile

| Rank | ICP | Why attractive | Initial motion |
| --- | --- | --- | --- |
| 1 | MSSPs and managed detection providers | Repeated investigations, analyst leverage, reusable playbooks, and a natural need for tenant separation | Design-partner pilot with one or two repeatable customer workflows |
| 2 | Mid-market enterprises already operating a SIEM | Clear pain from alert volume and limited analyst capacity without a rip-and-replace requirement | Founder-led pilot tied to a narrow alert family |
| 3 | Enterprise SOCs with investigation consistency goals | High value from governance, auditability, and analyst decision quality | Security architecture-led evaluation |
| 4 | Resource-constrained security teams | Strong time-to-value if integrations are limited and setup is simple | Productized pilot with a small evidence set |
| 5 | New SOC or SIEM-modernization programs | Longer sales cycle and greater platform expectations | Later expansion motion, not the first wedge |

The first beachhead is the team that already has alerts and evidence but needs
more investigation capacity. A customer should be able to adopt Sentinel DNA
without replacing its SIEM, endpoint platform, or intelligence providers.

## 3. Core product packaging

The package names below are working names and should be validated with design
partners.

### Sentinel DNA Investigator

- **Target:** Small SOCs, security consultants, and teams evaluating AI-assisted
  investigation.
- **Capabilities:** Alert intake, evidence collection, investigation plan,
  bounded AI execution, intelligence enrichment, analyst-readable reasoning,
  decision record, and exportable provenance.
- **Differentiator:** A complete evidence-to-decision case record rather than a
  chat interface that cannot show how its conclusion was reached.
- **Value:** Reduce time spent assembling facts and create consistent first-pass
  investigations.
- **Expansion:** More integrations, collaboration, retention, automation, and
  tenant administration.

### Sentinel DNA SOC

- **Target:** Mid-market and enterprise SOC teams.
- **Capabilities:** Investigator plus case queues, team workspaces, RBAC,
  SSO/OIDC, audit history, integrations, retention policy, approval workflows,
  and operational reporting.
- **Differentiator:** Governed investigation orchestration that remains
  reviewable by analysts and security leadership.
- **Value:** Increase analyst throughput while improving investigation
  consistency and audit readiness.
- **Expansion:** Multiple teams, larger evidence workloads, API access, and
  advanced automation.

### Sentinel DNA Enterprise

- **Target:** Regulated enterprises and large distributed SOCs.
- **Capabilities:** SOC package plus multi-tenancy or organizational partitions,
  delegated administration, private connectivity options, compliance evidence,
  granular policy controls, data residency choices, advanced retention, and
  enterprise support.
- **Differentiator:** Evidence provenance and deterministic replay as governed
  enterprise capabilities, not optional AI explanations.
- **Value:** Make AI-assisted investigation operationally trustworthy at scale.
- **Expansion:** MSSP operations, additional business units, and high-assurance
  deployment models.

### MSSP operating model

MSSP support should be an expansion capability with tenant isolation, delegated
  administration, per-tenant evidence boundaries, customer-visible audit
  records, and usage allocation. It should not be implemented by weakening
  tenancy or sharing privileged credentials.

## 4. AI Investigator wedge

The minimum compelling experience is a narrow, reliable workflow for one or two
high-frequency alert families. It should demonstrate:

`Alert -> Evidence -> Investigation Plan -> Execution -> Intelligence -> Reasoning -> Decision -> Analyst Action`

### Minimum experience

1. Accept an alert with a stable case identifier.
2. Display the initial facts and explicitly identify missing evidence.
3. Produce a bounded investigation plan with intended tools and questions.
4. Collect evidence through approved provider adapters, recording source,
   timestamp, status, and provenance.
5. Enrich indicators through provider-neutral intelligence interfaces.
6. Present findings with citations to evidence and clear uncertainty labels.
7. Generate a risk/decision recommendation with the reasoning chain visible to
   the analyst.
8. Allow the analyst to approve, reject, or defer an action.
9. Preserve the complete event, evidence, tool-result, reasoning, and decision
   record for replay and review.

### Demonstration boundary

The first demo should prioritize one end-to-end path that works repeatedly over
many shallow integrations. Actions should be approval-gated and reversible in
the demo environment. The AI must not imply that an unverified conclusion is a
fact or that a recommendation is an executed response.

## 5. Enterprise feature roadmap

### MVP

- Single organization boundary with explicit tenant identity in domain objects.
- Basic analyst and reviewer roles.
- Case and evidence audit trail.
- Provider adapter interfaces with controlled timeouts and failure states.
- API surface for alert intake and investigation retrieval.
- Configurable evidence retention for pilot data.
- Exportable provenance record.
- Usage counters for investigations, evidence operations, and AI execution.
- Existing release and deployment fail-closed controls preserved.

### Enterprise expansion

- Strong tenant isolation with authorization tests and negative-path coverage.
- SSO/OIDC with mapped roles and lifecycle controls.
- Fine-grained RBAC and delegated administration.
- Immutable or append-only audit export appropriate to the deployment model.
- Broader API, webhooks, SDK, and integration catalog.
- Retention, legal hold, deletion, residency, and encryption policy controls.
- Usage metering, budgets, quotas, and customer-visible consumption reports.
- Compliance evidence packages and independent control attestations.
- Multi-region or private connectivity options where commercially justified.
- MSSP parent/child tenant operations with strict evidence boundaries.

Security, privacy, and operability must be acceptance criteria for each feature,
not a hardening phase after the feature is sold.

## 6. Monetization

### Recommended primary metric

Use a platform subscription based on **investigator capacity**—licensed analyst
cohorts or operational teams—with a generous included investigation allowance
and transparent guardrails for exceptional compute or evidence volume.

This aligns price with the value Sentinel DNA creates: more analyst capacity and
faster decisions. Pricing solely on alerts, raw ingestion, or every evidence
event can punish customers for investigating more thoroughly and would place
Sentinel DNA in a direct SIEM-ingestion comparison.

Potential secondary dimensions are retention, premium integrations, dedicated
capacity, and unusually high AI/evidence compute. These should be framed as
capacity or service-level choices, not surprise charges for ordinary analyst
work.

### Packaging hypothesis

- **Demo:** Time-boxed, synthetic or approved sample data, one guided workflow,
  no production action capability.
- **Starter:** One team, core Investigator workflow, a small integration set,
  standard retention, and exportable evidence.
- **Professional:** Multiple workflows, collaboration, SSO, expanded
  integrations, API access, and operational reporting.
- **Enterprise:** Custom tenancy, governance, retention, support, residency,
  private connectivity, and reviewable compliance evidence.
- **MSSP:** Parent/child tenancy, delegated administration, tenant-level usage,
  customer reporting, and service-provider controls.

The tier boundaries and price points are commercial hypotheses to validate with
design partners; no market price is asserted here. Test willingness to pay
against time saved, investigation quality, and auditability.

## 7. Customer value and telemetry

Measure outcomes at case level and report them without exposing customer
content. Candidate metrics include:

- Median time from alert acceptance to first defensible decision.
- Median evidence-collection time and evidence completeness by workflow.
- Analyst minutes saved relative to a documented baseline.
- Percentage of cases with a complete provenance trail.
- Investigation plan execution success and provider failure rates.
- Percentage of AI findings accepted, edited, rejected, or escalated.
- Reopen and rework rates.
- Consistency of disposition for comparable cases.
- Automation/approval rate for bounded actions.
- Mean time to investigate and time to contain, where customer policy permits.
- Analyst review and correction patterns, with privacy-preserving aggregation.

Every metric needs a defined event schema, tenant scope, retention policy, and
quality caveat before it becomes a sales claim. Pilot success should compare a
baseline workflow with a Sentinel DNA workflow on the same alert family.

## 8. Commercial differentiation

### Current advantage

- Evidence-first AI investigation rather than unsupported conversational output.
- Investigation provenance that links conclusions to collected evidence.
- A deterministic, replay-oriented execution model.
- Provider-neutral intelligence and evidence interfaces.
- A decision record that makes analyst approval explicit.
- Release and deployment controls that support high-assurance operation.

### Potential moat

- A permissioned corpus of investigation plans, evidence patterns, outcomes, and
  analyst corrections.
- Replayable investigation traces that reveal which evidence changed a decision.
- Organization-specific investigation memory that is bounded, reviewable, and
  tenant-isolated.
- A graph linking alerts, evidence, indicators, hypotheses, decisions, and
  actions.
- Workflow-level quality measurement and feedback loops.
- Integrations that preserve provenance across heterogeneous providers.

The moat must be earned through customer-authorized data, strong privacy
controls, and demonstrable improvement. Customer data must never be treated as
an unbounded training asset by default.

## 9. Ten-minute enterprise demonstration

1. **Alert arrives:** Show a representative suspicious identity or endpoint
   alert with a stable case ID.
2. **Case opens:** Display scope, initial facts, confidence, and missing facts.
3. **Evidence collection:** Start the bounded plan and show source, timestamp,
   status, and provenance as evidence arrives.
4. **IOC intelligence:** Enrich an indicator through a provider-neutral adapter;
   show provider attribution and uncertainty.
5. **AI investigation:** Execute the plan with visible steps and controlled
   failure handling.
6. **MITRE context:** Map relevant behavior to technique context without
   presenting the mapping as proof of compromise.
7. **Reasoning:** Show the evidence-backed hypothesis, counter-evidence, and
   confidence.
8. **Decision:** Present risk, recommended disposition, and unresolved
   questions.
9. **Analyst action:** Let the analyst approve a bounded action or record a
   decision to escalate; do not imply that approval equals execution.
10. **Provenance:** Open the full replay/evidence trail and export a reviewer-
    friendly case record.

The memorable contrast is not “another dashboard.” It is “the analyst can see
what was asked, what was observed, why the conclusion follows, and what remains
uncertain.”

## 10. Go-to-market

### First channel: founder-led design-partner sales

Start with a narrow alert family and a measurable baseline. The founder or CTO
should qualify the evidence workflow, security constraints, and decision-maker
before promising integrations. The objective is learning and referenceability,
not broad logo accumulation.

### Second channel: MSSP and SOC consulting partnerships

Partner with firms that already perform investigations and can expose repeated
workflow pain. Structure the first engagements around a controlled pilot,
tenant boundaries, and analyst feedback. Avoid channel scale until the product
can support repeatable onboarding and auditable customer separation.

Universities and security labs are useful for demonstrations and research
credibility, but should support—not replace—the first paid customer motion.

## 11. Product roadmap

### Phase A — Commercial Demo

- **Objective:** Prove the evidence-first investigation story in ten minutes.
- **Features:** One or two alert families, synthetic/sample data, bounded
  adapters, replayable case record, analyst decision step, provenance export.
- **Security requirements:** No production actions, fake or approved data only,
  explicit approval boundaries, no secret disclosure, and frozen-release
  controls preserved.
- **Customer evidence:** Recorded walkthrough, repeatable case outputs, and
  analyst feedback from design partners.
- **Exit criteria:** Three consecutive successful demonstrations, clear before/
  after workflow narrative, and no unexplained provenance gaps.

### Phase B — Pilot Ready

- **Objective:** Prove measurable value in a bounded customer environment.
- **Features:** Alert intake, selected integrations, team workspace, basic RBAC,
  SSO plan, retention policy, API export, telemetry, and support runbook.
- **Security requirements:** Tenant boundary tests, secret custody, approved
  TLS, audit logging, failure handling, privacy review, and an authorized
  validation-only release process.
- **Customer evidence:** Baseline versus assisted investigation metrics,
  customer-approved case samples, and support/escalation records.
- **Exit criteria:** At least one controlled pilot completes its agreed workflow
  with measurable time or consistency improvement and no unresolved critical
  security finding.

### Phase C — Production SaaS

- **Objective:** Operate repeatable, supportable customer workloads.
- **Features:** Production tenancy, SSO/OIDC, RBAC, integrations, retention,
  metering, incident operations, audit exports, and versioned APIs.
- **Security requirements:** Independent review, threat modeling, backup and
  recovery, monitoring, vulnerability management, compliant release gates, and
  customer data governance.
- **Customer evidence:** Production service levels, adoption/retention data,
  support performance, and verified outcome telemetry.
- **Exit criteria:** Repeatable onboarding, documented operational ownership,
  successful recovery exercises, and approved production release governance.

### Phase D — Enterprise Scale

- **Objective:** Support complex enterprises and MSSP operations without losing
  evidence integrity.
- **Features:** Advanced tenancy, delegated administration, residency/private
  connectivity, policy engine, high-scale integrations, compliance packages,
  and organization-specific investigation memory.
- **Security requirements:** Formal control ownership, continuous assurance,
  stronger isolation evidence, key-management options, and independent audits
  appropriate to target markets.
- **Customer evidence:** Multi-team adoption, renewal/expansion, audit outcomes,
  measurable investigation quality, and validated capacity assumptions.
- **Exit criteria:** Enterprise references, predictable unit economics,
  supportable SLOs, and no material compromise of provenance or replayability.

## 12. Architecture preservation

Commercial work must be additive, modular, and independently testable. The
following are protected architectural contracts:

- `InvestigationCoordinator` remains the coordination boundary.
- `InvestigationOrchestrator` remains responsible for investigation workflow
  semantics.
- `RuntimeTaskExecutor` remains bounded, observable, and policy-controlled.
- `InvestigationResult` remains a stable contract for evidence-backed output.
- Evidence provenance, source attribution, timestamps, and replay identity must
  survive every integration and export.
- Intelligence providers remain behind provider-neutral interfaces.
- Tenant identity and authorization must be explicit in every persisted and
  externally addressable object.
- Deployment release manifests, image-digest requirements, protected metadata,
  and fail-closed controls must not be relaxed for sales speed.

Do not fold billing, generic data ingestion, or broad SIEM functions into core
investigation logic. Prefer adapters, policy modules, APIs, and separate
administrative surfaces.

## 13. Competitive strategy matrix

This matrix is a strategic framing tool, not a factual product benchmark.

| Capability | Sentinel DNA focus | Large security platform posture | Commercial implication |
| --- | --- | --- | --- |
| SIEM depth | Integrates with existing sources; does not lead with broad ingestion | Often a major platform strength | Avoid rip-and-replace positioning |
| AI investigation | Primary wedge and workflow | Varies by product and packaging | Demonstrate a complete, bounded case flow |
| Evidence provenance | Core product contract | May be distributed across platform records | Make lineage visible and exportable |
| Investigation automation | Orchestrated, approval-aware execution | Often tied to product-specific ecosystems | Win on portability and transparency |
| Decision intelligence | Explicit risk, uncertainty, and analyst decision record | Often present but not necessarily the primary wedge | Sell defensible decisions, not just detections |
| Analyst workflow | Investigator-centered case experience | Commonly broader SOC suites | Reduce cognitive load in the investigation step |
| Deployment flexibility | Preserve controlled, high-assurance release boundary | Varies by platform and edition | Make custody and provenance part of trust story |
| Provider neutrality | Adapter-oriented by design | Ecosystem depth can create lock-in | Integrate first; replace only when justified |
| Deterministic replay | Potential signature capability | Not the default buying language | Turn replay into audit and quality evidence |

## 14. Product moat

Prioritize moats that compound from real investigations:

1. **Investigation graph:** Link alerts, evidence, hypotheses, indicators,
   decisions, and actions with provenance.
2. **Replayable traces:** Re-run approved workflows against retained or
   redacted evidence to explain drift and improve quality.
3. **Analyst feedback:** Capture corrections and approvals as structured,
   tenant-scoped signals rather than opaque ratings.
4. **Organization-specific memory:** Store approved investigation patterns with
   clear retention, access, and deletion policy.
5. **Quality datasets:** Build permissioned evaluation sets from real workflows,
   including counter-evidence and failure cases.
6. **Provider-neutral correlation:** Preserve the same investigation semantics
   across changing intelligence and security providers.

These are potential moats, not current claims. They require governance,
privacy, explainability, and measurable lift before they become commercial
advantages.

## 15. Founder priority

### DO NOW

- Nail one evidence-first investigation workflow and its ten-minute demo.
- Recruit a small set of MSSP and mid-market design partners.
- Define a baseline and instrument investigation time, evidence completeness,
  decision quality, and analyst corrections.
- Productize provenance, replay, and reviewer-friendly exports.
- Document the security/custody boundary and preserve the frozen release.
- Validate packaging language and willingness-to-pay hypotheses.

### DO NEXT

- Add the integrations required by the first repeatable alert families.
- Deliver pilot-grade tenancy, RBAC, SSO/OIDC, audit, retention, and support
  workflows.
- Build customer-safe APIs and usage metering.
- Establish independent security review and operational readiness for approved
  production pilots.
- Turn pilot outcomes into referenceable evidence and repeatable onboarding.

### DO LATER

- Advanced MSSP hierarchy, residency options, private connectivity, and broad
  compliance packages.
- Large integration catalogs and organization-specific investigation memory.
- Advanced billing dimensions, capacity optimization, and large-scale
  performance work.
- Adjacent SOAR, threat-intelligence, payment, or data-platform expansion only
  where validated by customer demand.

### DO NOT BUILD YET

- A generic SIEM ingestion and retention replacement.
- Dozens of shallow integrations before one workflow is excellent.
- Autonomous destructive response actions.
- Opaque model fine-tuning on customer data by default.
- Complex billing before value and usage events are measured.
- Enterprise feature checklists without tenant, audit, and release evidence.

## 16. Definition of commercially ready

Sentinel DNA is commercially ready in stages, not as one binary claim:

- **Demo ready:** The core workflow is repeatable, understandable, and
  evidence-backed using approved data.
- **Pilot ready:** A bounded customer can connect approved evidence sources,
  measure a baseline, operate with documented custody/security controls, and
  receive support without bypassing release gates.
- **Security ready:** Threat model, tenant boundaries, secret custody, TLS,
  auditability, release evidence, and independent review are appropriate to the
  pilot or production scope.
- **Enterprise ready:** Governance, SSO/RBAC, retention, API, support, privacy,
  compliance evidence, recovery, and scale assumptions are demonstrated rather
  than merely planned.
- **Operationally ready:** Ownership, monitoring, incident response, rollback,
  release approval, and customer communication are tested and authorized.
- **Value ready:** Customers can show measurable reduction in investigation
  effort or time, improved evidence completeness/consistency, and a decision
  quality outcome they are willing to pay to preserve.

The current frozen release is engineering- and artifact-certified, but it is
not production-ready or commercially proven until the external custody,
governance, operational, and customer-value evidence exists.

## 17. Safety boundary and current release status

This blueprint does not change the certified release or production boundary.

- Certified release: unchanged.
- Deployment: not performed.
- Production mutation: none.
- Secrets: not accessed.
- TLS: not changed.
- Trusted metadata: not changed.
- Commit: not created.
- Remote push: not performed.
- Gate 1: remains blocked.
- Release freeze: remains intact.

COMMERCIAL READINESS BLUEPRINT CREATED

PRODUCTION RELEASE REMAINS BLOCKED

RELEASE FREEZE REMAINS INTACT
