# AI SOC Command Center Foundation

This package is the analyst-facing presentation/API orchestration layer over the existing Command Surface, Platform Intelligence Fabric, Analyst Workspace, Copilot, Evidence Engine, risk, compliance, governance, operations, lifecycle, outcome, optimization, and SOAR owners. It normalizes context for overview, attention, investigations, evidence, decisions, executive summaries, subsystem availability, provenance, uncertainty, and human review.

It does not create another intelligence engine, workspace, Copilot, or authentication system. It does not execute, approve, remediate, mutate controls/detections/playbooks/workflows/policies, certify compliance, store credentials, or make autonomous decisions. TTS is optional, disabled by default, and represented only as a presentation seam. The Flask blueprint is intentionally injectable so the existing authenticated tenant resolver can be supplied; callers must not rely on frontend filtering.

Phase 35.2 adds contextual navigation, breadcrumbs, tenant-scoped drill-down, provenance references, historical context, Copilot context routing, and unavailable-evidence handling. Drill-down resolves records through an injected authoritative source resolver and returns `not_found` for cross-tenant references; it never creates investigations or performs lifecycle transitions. Existing investigation, evidence, risk, compliance, governance, lifecycle, Workspace, Copilot, Fabric, and TTS ownership remains unchanged.

Phase 35.3 adds a deterministic normalized analyst event model and polling-first `AnalystEventFeed`. Events retain source references, provenance, confidence, uncertainty, navigation metadata, and advisory/human-review boundaries. Retrieval supports tenant-safe filtering, time ranges, entity/investigation history, latest events, deduplication, and presentation-only acknowledgement. The repository is replaceable for SQLite/PostgreSQL. No SSE/WebSocket, telemetry engine, SIEM, raw sensitive payloads, or authoritative mutation is introduced; future streaming can consume the same feed contract.

Phase 35.4 derives `AttentionItem` records from the event feed. Ordering is deterministic: presentation priority, severity, human-review requirement, recency, and stable ID; authoritative source priority and severity are preserved separately. Related events are clustered by tenant, type, source domain, and source reference, with recurring counts and event references retained. Acknowledgement and defer are analyst presentation state only. The layer remains advisory, evidence-aware, tenant isolated, polling-compatible, and does not replace risk, evidence, investigation, compliance, governance, lifecycle, or telemetry ownership.
## Decision Context

The Command Center presents an evidence-first, tenant-scoped `DecisionContext` that organizes attention, authoritative references, timeline, uncertainty, recommendations, and decision history for human analysts. Decision questions are deterministic and are not fabricated when no decision is required. Missing evidence or degraded subsystems preserve uncertainty and require human review.

Phase 35.6 adds the read-only `AnalystInvestigationWorkspace` composition layer and `GET /api/command-center/investigation/<investigation_id>/workspace`. It combines tenant-scoped attention, AnalystEvent records, authoritative investigation/evidence references, and existing DecisionContext data into one normalized analyst view. Missing sources are represented as unavailable/degraded, with provenance, uncertainty, and human-review requirements preserved. The repository/service boundary remains replaceable for future persistence backends.

This workspace does not create or execute investigations, replace the Evidence Engine, change lifecycle state, approve decisions, execute SOAR actions, or create another Workspace, Copilot, Fabric, risk, or intelligence engine. Cross-tenant resources resolve as not found, and navigation entries are references only.

Phase 35.7 adds deterministic `AnalystNextStep` actionability over the workspace through `GET /api/command-center/investigation/<investigation_id>/next-steps`. Recommendations carry machine-readable reasons, source references, navigation references, confidence, uncertainty, and explicit human-review status. They are advisory-only value objects: no executable command, automation payload, external URL, mutation, SOAR invocation, or external call is supported. Ordering is stable for identical tenant/workspace state, and inaccessible investigations return `404` through the existing tenant boundary.

Phase 35.8 adds deterministic `InvestigationOutcome` intelligence through `GET /api/command-center/investigation/<investigation_id>/outcome`. It summarizes evidence-supported analytical outcomes, decision/event references, unresolved items, confidence, provenance, uncertainty, and human-review requirements. An outcome is not case closure, incident resolution, severity/priority mutation, or lifecycle state: authoritative case and lifecycle systems remain the owners. No outcome is persisted independently, and insufficient or uncertain evidence is never converted into a benign or confirmed conclusion. Future outcome analytics may consume this metadata, but analytics, automation, execution, remediation, and external integrations are explicit non-goals.

Phase 35.9 adds tenant-scoped `AnalystInvestigationFeedback` and deterministic `InvestigationQualitySignal` views through `GET` and validated `POST /api/command-center/investigation/<investigation_id>/feedback`. Analyst feedback is an evaluation signal, not an authoritative state mutation. Feedback preserves history, provenance, and structured agreement/evidence/recommendation assessments; disagreement never rewrites the outcome, evidence, investigation, case, or lifecycle. Missing feedback is reported as `insufficient_data`, and quality reasons remain explainable. The in-memory repository is replaceable and introduces no second database. No ML, LLM, autonomous learning, dashboards, notifications, execution, or external integrations are included.

Phase 35.10 adds read-only quality-trend aggregation at `GET /api/command-center/quality/trends`. `AnalystQualityTrend` derives stable counts, confidence, disagreement, evidence insufficiency, unresolved quality, human-review, uncertainty, provenance, and contributing references exclusively from the existing tenant-scoped feedback repository and quality signals. Empty or insufficient data remains explicit; no trend implies model accuracy. This layer does not mutate feedback, investigation, outcome, case, lifecycle, or authoritative intelligence, and does not implement ML training, autonomous learning, dashboards, or external integrations.

Phase 35.11 adds read-only `AnalystQualityIntelligence` at `GET /api/command-center/quality/intelligence`, composed from the Phase 35.10 trend contract. It exposes deterministic analyst attention items for recurring disagreement, evidence insufficiency, unresolved quality, human review, uncertainty, and insufficient data. Stable IDs, priorities, reasons, provenance, confidence, and contributing references are preserved. It is an advisory presentation layer only: it does not mutate feedback or authoritative systems, execute actions, or introduce ML, LLM, remediation, SOAR, or external integrations.

Phase 35.12 adds read-only `AnalystInvestigationLearning` at `GET /api/command-center/quality/learning`, derived exclusively from existing quality intelligence/trend contracts. It identifies recurring disagreement, evidence gaps, unresolved and human-review patterns, low confidence, uncertainty, degradation, positive quality, or explicit insufficient data using simple documented deterministic rules. Learning items preserve provenance, confidence, uncertainty, contributing references, stable IDs, and advisory analyst focus. This layer observes quality intelligence; it does not own quality truth, train models, mutate investigations, or execute actions.

This layer is advisory only: it does not replace investigation, evidence, risk, compliance, governance, or lifecycle intelligence; approve or execute actions; remediate incidents; modify controls, detections, or workflows; or certify compliance. Authoritative state remains owned by its source systems. Actions are navigation references only. Platform Fabric references, Analyst Workspace navigation, and the existing Copilot provider remain compatible; Copilot cannot mutate decision or authoritative state. TTS remains optional, disabled by default, presentation-only, and independent of decision assembly.

All decision reads require tenant scope, and cross-tenant resources are treated as not found. Historical state is shown only when available; otherwise it is `unavailable`. The context preserves provenance, confidence, uncertainty, advisory status, and the human-review boundary.
## Phase 35.13 — Longitudinal learning effectiveness

`AnalystLearningEffectivenessService` compares chronological observations produced by the existing learning layer. It is read-only, tenant-scoped, deterministic, advisory, and does not create a feedback store or mutate authoritative state.

Effectiveness is classified as `improving`, `degrading`, `mixed`, `stable`, or `insufficient_data`. The bounded score is the mean of later-minus-earlier normalized quality dimensions; lower-is-better rates are inverted, and the result is clamped to `-1.0..1.0`. Changes below `0.05` are treated as stable. This calculation is explainable from observable inputs.

Confidence increases with observation count and temporal persistence. Uncertainty records applicable limitations such as insufficient observations, insufficient temporal span, low feedback coverage, incomplete provenance, and mixed signals. Results include contributing feedback, investigation, learning, and outcome references without fabricating missing outcomes.

The read-only endpoint is `/api/command-center/quality/effectiveness`. Effectiveness indicates an evidence-backed association between learning signals and later investigation-quality outcomes. It does not establish causation.
## Analyst learning feedback loop

The read-only `/api/command-center/quality/learning-feedback` endpoint closes the evidence-backed intelligence loop from investigation outcomes and quality signals through analyst learning and longitudinal effectiveness. `AnalystLearningFeedbackService` composes the existing learning and effectiveness services; it does not retrain models or make decisions.

Feedback states include `improving`, `degrading`, `stable`, `mixed`, `insufficient_data`, `new_pattern`, `resolved_pattern`, and `persistent_pattern`. IDs, ordering, classifications, uncertainty, and provenance are deterministic and tenant-scoped. Each observation retains upstream source names and contributing references, and is explicitly advisory-only. Future expansion may add persisted evaluation snapshots while preserving the same tenant boundary and read-only safety contract.

## Organizational learning intelligence

`/api/command-center/quality/organizational-learning` provides tenant-scoped, read-only organizational observations composed from investigation learning, effectiveness, and learning feedback. It detects recurring disagreement, evidence gaps, unresolved investigations, human-review dependency, low confidence, uncertainty, quality changes, and persistent, emerging, or resolved patterns. Results include deterministic IDs and ordering, explainable classifications, confidence, uncertainty, provenance, contributing references, team focus, and `advisory_only: true`.

The service performs no remediation, enforcement, investigation mutation, quality-history mutation, or model retraining. Future expansion can add historical organizational comparisons and explicit team dimensions without weakening tenant isolation or the advisory boundary.

## Executive Learning Dashboard

The protected `/workspace/executive-learning` page is a read-only presentation layer over `/api/command-center/quality/executive-learning`. It presents posture, KPI counts, signal distribution, organizational dimensions, deterministic priority signals, evidence/confidence governance, provenance availability, and advisory focus recommendations. Values are rendered with safe DOM APIs; tenant identity remains server/API controlled.

Empty, partial, insufficient, unauthorized, and failed API states are surfaced as explicit unavailable or safe error messages. The dashboard does not recalculate intelligence, fabricate historical series, execute recommendations, or mutate platform state. It is intentionally separate from the intelligence services so future drill-down and trend visualization can be added without changing upstream contracts.

## Executive organizational learning intelligence

`/api/command-center/quality/executive-learning` composes historical organizational trends into deterministic executive signals and a tenant-scoped summary. Classifications are explicitly prioritized as critical gaps, persistent gaps, degrading, improving, emerging, resolved, mixed, stable, or insufficient data. Signal ordering never depends on lexical ordering.

Relevance is bounded to `0..1` and is explainable: upstream confidence is combined with evidence strength and a bounded classification factor; uncertainty reduces evidence strength rather than being hidden. Organizational scope and team focus are populated only when upstream data provides them; missing dimensions remain unavailable. Provenance and contributing references are preserved, and observed association does not establish causation.

Executive signals are read-only, advisory decision support. They do not mutate investigations, execute actions, retrain models, persist recommendations, or replace analyst judgment. Future dashboard integration can consume the signal and summary contracts directly.

## Historical organizational trend intelligence

`/api/command-center/quality/organizational-trends` analyzes supplied historical organizational-learning snapshots without creating persistence. It supports `improving`, `degrading`, `stable`, `mixed`, `emerging`, `persistent`, `recurring`, `resolving`, `resolved`, and `insufficient_data`. Rules use deterministic temporal ordering: all-present histories are persistent, intermittent histories are recurring, newly present patterns are emerging, and absent recent patterns are resolving or resolved. Missing temporal coverage is explicitly insufficient data.

Trend records preserve tenant scope, upstream provenance, references, observation count, span, confidence, uncertainty, and an unavailable organizational dimension when source data does not provide one. Effectiveness is consumed as an upstream signal; observed association does not establish causation. The endpoint is read-only and advisory-only. Future phases may add persisted snapshots, legitimate team dimensions, visualizations, and executive reporting without changing this contract.

## Executive learning drill-down

`GET /api/command-center/quality/executive-learning/<signal_id>` provides tenant-scoped evidence traceability for one executive signal. It composes matching trend, organizational learning, effectiveness, feedback, safe references, dimensions, confidence, uncertainty, provenance, and advisory interpretation. Missing historical or team data is explicit rather than inferred.

The drill-down provides evidence traceability and decision support. It does not establish causation or authorize remediation, mutate state, expose raw private payloads, or reveal whether a signal belongs to another tenant.

## Organizational Maturity Intelligence

`GET /api/command-center/quality/maturity` exposes an internal, tenant-scoped maturity assessment composed from existing organizational learning and trend intelligence. Scores are bounded from 0–100 using explainable evidence-backed dimension mappings; confidence and evidence strength are reported separately. Levels are internal Sentinel DNA indicators, not industry certifications, compliance ratings, or external security rankings.

Historical benchmarking compares only against the same tenant's supplied historical evidence. Peer benchmarking is explicitly unavailable. Missing observations, temporal coverage, provenance, or dimensions remain uncertainty rather than being fabricated. The maturity API and dashboard integration are read-only and advisory-only.

## Executive SOC maturity reporting

`GET /api/command-center/quality/maturity/report` provides deterministic historical reporting over the canonical maturity score. It exposes score delta, trajectory, maturity transitions, dimension summaries, strongest and weakest dimensions, evidence strength, confidence, temporal span, uncertainty, provenance, and advisory recommendations. Historical observations are consumed only when explicitly available; no persistence or fabricated time series is introduced.

Trajectory classifications include improving, degrading, stable, sustained improvement/degradation, and insufficient data. Benchmarking is limited to the same tenant's historical baseline; peer benchmarking remains unavailable. Sentinel DNA maturity scores are internal evidence-based indicators, not industry certifications, compliance ratings, or external security rankings.

## Executive maturity dashboard

The protected `/workspace/maturity` page consumes `/api/command-center/quality/maturity/report` as a presentation-only source. It renders current score and level, trajectory, historical metadata, dimensions, strengths, weaknesses, signals, recommendations, evidence strength, confidence, provenance, and uncertainty with safe DOM APIs. JavaScript does not calculate maturity or reorder intelligence.

Insufficient history and API failures are shown explicitly. The dashboard is tenant-scoped, read-only, advisory-only, and makes no peer or external benchmark claims. Historical visualizations display only backend-provided observations; no sample points are fabricated.

## SOC improvement planning

`GET /api/command-center/quality/maturity/improvement` composes maturity reporting into comparative dimensions, deterministic improvement priorities, and advisory improvement plans. Plans include rationale, evidence references, expected outcomes, and future measurement criteria; they never execute actions. Relative positions are only within the tenant's available dimensions, not peer benchmarks. Weak evidence, missing dimensions, insufficient history, and unavailable impact data remain explicit uncertainty.
