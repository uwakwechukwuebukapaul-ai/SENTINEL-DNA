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
from sentinel_dna.risk.risk_engine import RiskEngine


class InvestigationOrchestrator:
    """
    Canonical Sentinel DNA investigation workflow engine.

    Responsible for:

    - investigation planning
    - runtime execution
    - evidence collection
    - IOC enrichment
    - correlation
    - MITRE mapping
    - risk analysis
    - reasoning
    - decision intelligence
    - reporting

    Architecture:

        InvestigationCoordinator
                 |
                 v
        InvestigationOrchestrator
                 |
        -------------------------
        |           |           |
     Planner    Runtime    Reporter

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


        context.trace.add_event(
            "investigation_started",
            "Investigation workflow started",
        )


        plan = self.planner.create_plan(
            context,
            self,
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

    def load_context(self, context: InvestigationContext) -> None:
        alert = self._validated_alert(context.alert)

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
            {"alert": alert},
        )

        self.case_store.save(case)

        context.alert = alert
        context.case = case

    def collect_evidence(self, context: InvestigationContext) -> None:
        evidence = self.evidence_engine.normalize_email(
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

        self.evidence_engine.save(evidence)

        context.evidence_items.append(evidence)

        context.iocs = sorted(
            set(evidence.indicators)
        )

        if context.case is not None:
            context.case.attach_evidence(
                evidence.evidence_id
            )
            self.case_store.save(context.case)

        if not context.iocs:
            context.uncertainties.append(
                "No IOCs were discovered in the submitted alert evidence."
            )

    def enrich_iocs(self, context: InvestigationContext) -> None:
        enriched: dict[str, dict[str, Any]] = {}

        for ioc in context.iocs:
            normalized_ioc = ioc.lower()

            if normalized_ioc.startswith(
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
                    term in normalized_ioc
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

        context.intelligence["iocs"] = enriched

    def correlate_entities(
        self,
        context: InvestigationContext,
    ) -> None:
        correlations: list[dict[str, Any]] = []

        for evidence in context.evidence_items:
            for ioc in evidence.indicators:
                correlations.append(
                    {
                        "evidence_id": evidence.evidence_id,
                        "indicator": ioc,
                        "relationship": "observed_in_evidence",
                    }
                )

        context.correlations = correlations

        if not correlations:
            context.uncertainties.append(
                "No event or entity correlations could be established "
                "from available evidence."
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
            if intelligence.get("reputation") == "suspicious"
        ]

        context.intelligence["threat"] = {
            "source": "local_rules",
            "suspicious_iocs": suspicious_iocs,
            "summary": (
                "Local indicator rules found suspicious IOCs."
                if suspicious_iocs
                else "No known suspicious IOCs found locally."
            ),
        }

    def map_mitre_attack(
        self,
        context: InvestigationContext,
    ) -> None:
        text = self._evidence_text(context).lower()

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
            mappings.append(
                {
                    "technique_id": "T1566",
                    "technique": "Phishing",
                    "evidence": "Credential-themed email content",
                }
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
                    "evidence": "Payment-themed alert content",
                }
            )

        context.mitre_attack = mappings

        if not mappings:
            context.uncertainties.append(
                "No MITRE ATT&CK technique could be mapped from "
                "current evidence."
            )

    def classify_threat(
        self,
        context: InvestigationContext,
    ) -> None:
        labels = [
            mapping["technique"]
            for mapping in context.mitre_attack
        ]

        classification = (
            "phishing"
            if "Phishing" in labels
            else "unknown"
        )

        context.threat_classification = {
            "classification": classification,
            "evidence_count": len(
                context.evidence_items
            ),
            "mapped_techniques": labels,
        }

    def calculate_risk(
        self,
        context: InvestigationContext,
    ) -> None:
        context.risk = self.risk_engine.assess(
            context.evidence_items
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
                / len(context.evidence_items)
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
                "Derived from evidence confidence, task errors, "
                "and unresolved uncertainty."
            ),
            "uncertainties": context.uncertainties,
        }

    def perform_reasoning(
        self,
        context: InvestigationContext,
    ) -> None:
        findings: list[dict[str, Any]] = []

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
            "conclusion": self._conclusion(context),
        }

    def generate_decision_intelligence(
        self,
        context: InvestigationContext,
    ) -> None:
        risk_level = (
            context.risk.level
            if context.risk is not None
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
                "Insufficient evidence for a conclusion.",
            ),
        }

    def produce_recommendations(
        self,
        context: InvestigationContext,
    ) -> None:
        """
        Produce recommendations through the canonical public
        reporting API.

        The important architectural point is that this does not
        instantiate or import the legacy InvestigationEngine.

        `self.investigation_engine` is the compatibility/public
        service alias pointing at InvestigationReporter.
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

    def generate_report(
        self,
        context: InvestigationContext,
    ) -> None:
        if (
            context.case is None
            or context.risk is None
        ):
            context.report = {
                "status": "incomplete",
                "reason": "Missing case or risk assessment.",
            }
            return

        summary = self.investigation_engine.summarize(
            context.case,
            context.evidence_items,
            context.risk,
            recommended_actions=context.recommendations,
        )

        context.report = {
            "executive_summary": summary.executive_summary,
            "key_findings": summary.key_findings,
            "recommended_actions": summary.recommended_actions,
            "confidence_statement": summary.confidence_statement,
        }

    def _assemble_results(
        self,
        context: InvestigationContext,
        plan: list[RuntimeTask],
    ) -> dict[str, Any]:
        risk = (
            None
            if context.risk is None
            else vars(context.risk)
        )

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
                vars(evidence)
                for evidence in context.evidence_items
            ],
            "iocs": context.iocs,
            "intelligence": context.intelligence,
            "correlations": context.correlations,
            "timeline": context.timeline,
            "mitre_attack": context.mitre_attack,
            "threat_classification": (
                context.threat_classification
            ),
            "risk": risk,
            "confidence": context.confidence,
            "reasoning": context.reasoning,
            "decision_intelligence": (
                context.decision_intelligence
            ),
            "recommendations": context.recommendations,
            "report": context.report,
            "audit_trail": context.audit_trail,
            "uncertainties": context.uncertainties,
        }

    def _validated_alert(
        self,
        alert: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(alert, dict):
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
        return " ".join(
            f"{evidence.summary} {evidence.raw}"
            for evidence in context.evidence_items
        )

    def _conclusion(
        self,
        context: InvestigationContext,
    ) -> str:
        risk_level = (
            context.risk.level
            if context.risk is not None
            else "unknown"
        )

        classification = (
            context.threat_classification.get(
                "classification",
                "unknown",
            )
        )

        if not context.evidence_items:
            return (
                "No evidence was collected; "
                "the investigation remains uncertain."
            )

        return (
            f"Available evidence supports a "
            f"{classification} classification with "
            f"{risk_level} risk."
        )
