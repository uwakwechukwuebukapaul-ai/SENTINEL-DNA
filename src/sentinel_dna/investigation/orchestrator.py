from pathlib import Path
from typing import Any

from sentinel_dna.case_management.case_store import CaseStore
from sentinel_dna.case_management.models import Case
from sentinel_dna.evidence.evidence_engine import EvidenceEngine
from sentinel_dna.investigation.context import InvestigationContext
from sentinel_dna.investigation.planning import InvestigationPlanner
from sentinel_dna.investigation.reporting import InvestigationReporter
from sentinel_dna.investigation.result import InvestigationResult
from sentinel_dna.investigation.runtime import (
    RuntimeTask,
    RuntimeTaskExecutor,
)
from sentinel_dna.investigation.trace_manager import attach_trace
from sentinel_dna.investigation.provenance import (
    InvestigationProvenance,
)
from sentinel_dna.investigation.replay import (
    InvestigationReplay,
)
from sentinel_dna.risk.risk_engine import RiskEngine


class InvestigationOrchestrator:
    """
    Canonical Sentinel DNA investigation workflow engine.

    Enterprise investigation workflow:

        Alert
          |
          v
    InvestigationContext
          |
          +----------------+
          |                |
       Graph          Provenance
          |                |
          +--------+-------+
                   |
              Replay Timeline
                   |
              InvestigationResult


    Responsible for:

    - investigation planning
    - runtime execution
    - evidence collection
    - IOC enrichment
    - entity correlation
    - MITRE ATT&CK mapping
    - risk analysis
    - reasoning
    - decision intelligence
    - reporting
    - investigation lineage
    """

    def __init__(
        self,
        data_dir: str | Path = "data",
        runtime: RuntimeTaskExecutor | None = None,
        planner: InvestigationPlanner | None = None,
        reporter: InvestigationReporter | None = None,
    ) -> None:

        self.case_store = CaseStore(data_dir)

        self.evidence_engine = EvidenceEngine(
            data_dir
        )

        self.risk_engine = RiskEngine()

        self.reporter = (
            reporter
            or InvestigationReporter()
        )

        # Backward compatibility contract
        self.investigation_engine = (
            self.reporter
        )

        self.runtime = (
            runtime
            or RuntimeTaskExecutor()
        )

        self.planner = (
            planner
            or InvestigationPlanner()
        )


    def run(
        self,
        context: InvestigationContext,
    ) -> InvestigationResult:
        """
        Execute complete investigation workflow.
        """

        if context.trace is None:
            attach_trace(context)


        self._initialize_lineage(
            context
        )


        self._record_replay(
            context,
            "investigation",
            "Investigation workflow started",
        )


        self._record_provenance(
            context,
            stage="orchestrator",
            action="investigation_started",
            source="InvestigationOrchestrator",
        )


        context.trace.add_event(
            "investigation_started",
            "Investigation workflow started",
        )


        plan = self.planner.create_plan(
            context,
            self,
        )


        self._record_replay(
            context,
            "planning",
            "Investigation execution plan generated",
            {
                "task_count": len(plan),
            },
        )


        context.trace.add_event(
            "plan_created",
            "Investigation execution plan generated",
            {
                "plan_name": self.planner.plan_name,
                "task_count": len(plan),
            },
        )


        self.runtime.execute(
            context,
            plan,
        )


        self._record_replay(
            context,
            "runtime",
            "Investigation tasks completed",
            {
                "task_count": len(
                    context.task_results
                ),
            },
        )


        self._record_provenance(
            context,
            stage="runtime",
            action="tasks_completed",
            source="RuntimeTaskExecutor",
        )


        context.trace.add_event(
            "tasks_completed",
            "Investigation tasks completed",
            {
                "task_count": len(
                    context.task_results
                ),
            },
        )


        results = self._assemble_results(
            context,
            plan,
        )


        context.trace.add_event(
            "generate_report",
            "Investigation report generated",
        )


        results["audit_trail"] = (
            context.trace.events
        )


        return InvestigationResult(
            plan_name=self.planner.plan_name,
            results=results,
            errors=context.errors,
        )


    def _initialize_lineage(
        self,
        context: InvestigationContext,
    ) -> None:

        if context.provenance is None:
            context.provenance = InvestigationProvenance(
                context.case_id
            )


        if context.replay is None:
            context.replay = InvestigationReplay(
                context.case_id
            )


    def _record_replay(
        self,
        context: InvestigationContext,
        stage: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:

        if context.replay:
            context.replay.add_event(
                stage,
                message,
                details,
            )


    def _record_provenance(
        self,
        context: InvestigationContext,
        stage: str,
        action: str,
        source: str,
        details: dict[str, Any] | None = None,
        confidence: float | None = None,
    ) -> None:

        if context.provenance:
            context.provenance.add(
                stage,
                action,
                source,
                details,
                confidence,
            )
    def load_context(
        self,
        context: InvestigationContext,
    ) -> None:

        alert = self._validated_alert(
            context.alert
        )

        title = str(
            alert.get("title")
            or alert.get("subject")
            or "Security alert"
        )

        severity = str(
            alert.get("severity")
            or "medium"
        ).lower()

        description = str(
            alert.get("description")
            or alert.get("body")
            or "Alert submitted for investigation."
        )

        case = Case(
            title=title,
            description=description,
            severity=severity,
            case_id=context.case_id,
        )

        case.add_event(
            "case_created",
            "Case created",
        )

        case.add_event(
            "investigation_triggered",
            "Investigation triggered",
            {
                "alert": alert
            },
        )

        self.case_store.save(
            case
        )

        context.alert = alert
        context.case = case


        self._record_provenance(
            context,
            stage="context",
            action="case_loaded",
            source="CaseStore",
            details={
                "case_id": context.case_id,
            },
        )


        self._record_replay(
            context,
            "context",
            "Case context loaded",
        )


    def collect_evidence(
        self,
        context: InvestigationContext,
    ) -> None:

        evidence = (
            self.evidence_engine
            .normalize_email(
                {
                    "sender": context.alert.get(
                        "sender",
                        "unknown sender",
                    ),
                    "subject": context.alert.get(
                        "subject",
                        context.alert.get(
                            "title",
                            "No subject",
                        ),
                    ),
                    "body": context.alert.get(
                        "body",
                        context.alert.get(
                            "description",
                            "",
                        ),
                    ),
                }
            )
        )


        self.evidence_engine.save(
            evidence
        )


        context.evidence_items.append(
            evidence
        )


        context.iocs = sorted(
            set(
                evidence.indicators
            )
        )


        if context.case is not None:
            context.case.attach_evidence(
                evidence.evidence_id
            )

            self.case_store.save(
                context.case
            )


        self._record_provenance(
            context,
            stage="evidence",
            action="evidence_collected",
            source="EvidenceEngine",
            details={
                "evidence_id": evidence.evidence_id,
                "ioc_count": len(context.iocs),
            },
            confidence=evidence.confidence,
        )


        self._record_replay(
            context,
            "evidence",
            "Evidence collection completed",
            {
                "evidence_id": evidence.evidence_id,
            },
        )


        if not context.iocs:
            context.uncertainties.append(
                "No IOCs were discovered in submitted alert evidence."
            )


    def enrich_iocs(
        self,
        context: InvestigationContext,
    ) -> None:

        enriched: dict[str, dict[str, Any]] = {}


        for ioc in context.iocs:

            normalized = ioc.lower()


            if normalized.startswith(
                (
                    "http://",
                    "https://",
                )
            ):
                indicator_type = "url"

            else:
                indicator_type = "email_or_domain"


            reputation = (
                "suspicious"
                if any(
                    term in normalized
                    for term in (
                        "login",
                        "verify",
                        "password",
                    )
                )
                else "unknown"
            )


            enriched[ioc] = {
                "indicator": ioc,
                "type": indicator_type,
                "source": "local_rules",
                "reputation": reputation,
            }


        context.intelligence["iocs"] = (
            enriched
        )


        self._record_provenance(
            context,
            stage="intelligence",
            action="ioc_enrichment_completed",
            source="Local IOC Rules",
            details={
                "ioc_count": len(enriched),
            },
        )


    def correlate_entities(
        self,
        context: InvestigationContext,
    ) -> None:

        correlations: list[dict[str, Any]] = []


        for evidence in context.evidence_items:

            evidence_node = context.graph.add_node(
                "evidence",
                evidence.evidence_id,
            )


            for ioc in evidence.indicators:

                ioc_node = context.graph.add_node(
                    "ioc",
                    ioc,
                )


                context.graph.add_edge(
                    evidence_node,
                    ioc_node,
                    "contains",
                )


                correlations.append(
                    {
                        "evidence_id": evidence.evidence_id,
                        "indicator": ioc,
                        "relationship": (
                            "observed_in_evidence"
                        ),
                    }
                )


        context.correlations = correlations


        self._record_provenance(
            context,
            stage="correlation",
            action="entity_correlation_completed",
            source="InvestigationGraph",
            details={
                "relationships": len(
                    correlations
                )
            },
        )


        if not correlations:
            context.uncertainties.append(
                "No event or entity correlations established."
            )

    def build_timeline(
        self,
        context: InvestigationContext,
    ) -> None:

        context.timeline = [
            {
                "timestamp": evidence.observed_at,
                "event": evidence.summary,
                "evidence_id": evidence.evidence_id,
            }
            for evidence in sorted(
                context.evidence_items,
                key=lambda item: item.observed_at,
            )
        ]


    def evaluate_threat_intelligence(
        self,
        context: InvestigationContext,
    ) -> None:

        suspicious_iocs = [
            ioc
            for ioc, intelligence in context.intelligence.get(
                "iocs",
                {},
            ).items()
            if intelligence.get(
                "reputation"
            ) == "suspicious"
        ]


        context.intelligence["threat"] = {
            "source": "local_rules",
            "suspicious_iocs": suspicious_iocs,
            "summary": (
                "Local indicator rules found suspicious IOCs."
                if suspicious_iocs
                else "No suspicious IOCs identified."
            ),
        }


    def map_mitre_attack(
        self,
        context: InvestigationContext,
    ) -> None:

        text = self._evidence_text(
            context
        ).lower()


        mappings: list[dict[str, str]] = []


        if any(
            term in text
            for term in (
                "password",
                "credential",
                "mfa",
                "verify",
                "login",
            )
        ):

            mapping = {
                "technique_id": "T1566",
                "technique": "Phishing",
                "evidence": (
                    "Credential-themed email content"
                ),
            }

            mappings.append(
                mapping
            )


            evidence_node = context.graph.add_node(
                "technique",
                "T1566",
                {
                    "name": "Phishing"
                },
            )

            for item in context.evidence_items:
                source = context.graph.add_node(
                    "evidence",
                    item.evidence_id,
                )

                context.graph.add_edge(
                    source,
                    evidence_node,
                    "maps_to",
                )


        if any(
            term in text
            for term in (
                "invoice",
                "wire",
            )
        ):

            mappings.append(
                {
                    "technique_id": "T1657",
                    "technique": "Financial Theft",
                    "evidence": (
                        "Payment-themed alert content"
                    ),
                }
            )


        context.mitre_attack = mappings


        self._record_provenance(
            context,
            stage="analysis",
            action="mitre_mapping_completed",
            source="RuleBasedMITREMapper",
            details={
                "techniques": mappings,
            },
        )


    def classify_threat(
        self,
        context: InvestigationContext,
    ) -> None:

        labels = [
            item["technique"]
            for item in context.mitre_attack
        ]


        context.threat_classification = {
            "classification": (
                "phishing"
                if "Phishing" in labels
                else "unknown"
            ),
            "evidence_count": len(
                context.evidence_items
            ),
            "mapped_techniques": labels,
        }


    def calculate_risk(
        self,
        context: InvestigationContext,
    ) -> None:

        context.risk = (
            self.risk_engine.assess(
                context.evidence_items
            )
        )


    def calculate_confidence(
        self,
        context: InvestigationContext,
    ) -> None:

        if not context.evidence_items:
            score = 0.0

        else:
            score = (
                sum(
                    evidence.confidence
                    for evidence in context.evidence_items
                )
                /
                len(context.evidence_items)
            )

            if context.errors:
                score -= 0.15

            if context.uncertainties:
                score -= 0.10


        context.confidence = {
            "score": round(
                max(
                    0.0,
                    min(
                        1.0,
                        score,
                    ),
                ),
                2,
            ),
            "basis": (
                "Evidence confidence, execution errors, "
                "and uncertainty analysis."
            ),
            "uncertainties": context.uncertainties,
        }


    def perform_reasoning(
        self,
        context: InvestigationContext,
    ) -> None:

        findings = []

        for evidence in context.evidence_items:
            findings.append(
                {
                    "claim": evidence.summary,
                    "evidence_id": evidence.evidence_id,
                    "confidence": evidence.confidence,
                }
            )


        context.reasoning = {
            "mode": "evidence_grounded_rules",
            "findings": findings,
            "conclusion": self._conclusion(
                context
            ),
        }


    def generate_decision_intelligence(
        self,
        context: InvestigationContext,
    ) -> None:

        risk_level = (
            context.risk.level
            if context.risk
            else "unknown"
        )


        context.decision_intelligence = {
            "risk_level": risk_level,
            "confidence_score": context.confidence.get(
                "score",
                0.0,
            ),
            "recommended_decision": (
                "escalate"
                if risk_level in {
                    "critical",
                    "high",
                }
                else "monitor"
            ),
            "rationale": context.reasoning.get(
                "conclusion",
                "",
            ),
        }
    def produce_recommendations(
        self,
        context: InvestigationContext,
    ) -> None:
        """
        Generate response recommendations using the
        canonical reporting API.

        Maintains compatibility with the existing
        InvestigationReporter contract.
        """

        risk_level = (
            context.risk.level
            if context.risk is not None
            else "low"
        )

        context.recommendations = (
            self.investigation_engine.recommend_actions(
                risk_level
            )
        )


        self._record_provenance(
            context,
            stage="decision",
            action="recommendations_generated",
            source="InvestigationReporter",
            details={
                "risk_level": risk_level,
            },
        )


        self._record_replay(
            context,
            "decision",
            "Recommendations generated",
        )


    def generate_report(
        self,
        context: InvestigationContext,
    ) -> None:
        """
        Generate analyst-facing investigation report.
        """

        if (
            context.case is None
            or context.risk is None
        ):
            context.report = {
                "status": "incomplete",
                "reason": (
                    "Missing case or risk assessment."
                ),
            }

            return


        summary = (
            self.investigation_engine.summarize(
                context.case,
                context.evidence_items,
                context.risk,
                recommended_actions=(
                    context.recommendations
                ),
            )
        )


        context.report = {
            "executive_summary": (
                summary.executive_summary
            ),
            "key_findings": (
                summary.key_findings
            ),
            "recommended_actions": (
                summary.recommended_actions
            ),
            "confidence_statement": (
                summary.confidence_statement
            ),
        }


        self._record_provenance(
            context,
            stage="reporting",
            action="report_generated",
            source="InvestigationReporter",
        )


        self._record_replay(
            context,
            "reporting",
            "Investigation report generated",
        )

    def _assemble_results(
        self,
        context: InvestigationContext,
        plan: list[RuntimeTask],
    ) -> dict[str, Any]:

        return {
            "investigation": {
                "case_id": context.case_id,
                "plan_name": self.planner.plan_name,
                "status": (
                    "completed_with_errors"
                    if context.errors
                    else "completed"
                ),
            },

            "case_id": context.case_id,
            "alert": context.alert,

            "plan": {
                "name": self.planner.plan_name,
                "tasks": [
                    task.name
                    for task in plan
                ],
            },

            "tasks": context.task_results,

            "evidence": [
                vars(item)
                for item in context.evidence_items
            ],

            "iocs": context.iocs,
            "intelligence": context.intelligence,
            "correlations": context.correlations,
            "timeline": context.timeline,

            "graph": (
                context.graph.to_dict()
            ),

            "provenance": (
                context.provenance.to_dict()
                if context.provenance
                else {}
            ),

            "replay": (
                context.replay.to_dict()
                if context.replay
                else {}
            ),

            "mitre_attack": context.mitre_attack,
            "threat_classification": context.threat_classification,
            "risk": (
                vars(context.risk)
                if context.risk
                else None
            ),

            "confidence": context.confidence,
            "reasoning": context.reasoning,
            "decision_intelligence": context.decision_intelligence,
            "recommendations": context.recommendations,
            "report": context.report,
            "uncertainties": context.uncertainties,
        }


    def _validated_alert(
        self,
        alert: dict[str, Any],
    ) -> dict[str, Any]:

        if not isinstance(
            alert,
            dict,
        ):
            raise TypeError(
                "alert must be a dictionary"
            )

        return {
            str(key): value
            for key, value in alert.items()
        }


    def _evidence_text(
        self,
        context: InvestigationContext,
    ) -> str:

        if not context.iocs:
            context.uncertainties.append(
                "No IOCs were discovered in the submitted alert evidence."
            )

        return " ".join(
            f"{item.summary} {item.raw}"
            for item in context.evidence_items
        )


    def _conclusion(
        self,
        context: InvestigationContext,
    ) -> str:

        classification = (
            context.threat_classification.get(
                "classification",
                "unknown",
            )
        )

        risk = (
            context.risk.level
            if context.risk
            else "unknown"
        )


        return (
            f"Available evidence supports "
            f"{classification} classification "
            f"with {risk} risk."
        )