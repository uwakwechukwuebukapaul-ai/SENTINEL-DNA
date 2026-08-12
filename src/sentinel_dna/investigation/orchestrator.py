from pathlib import Path
from typing import Any

from sentinel_dna.case_management.case_store import CaseStore
from sentinel_dna.case_management.models import Case

from sentinel_dna.evidence.evidence_engine import EvidenceEngine

from sentinel_dna.investigation.context import (
    InvestigationContext,
)

from sentinel_dna.investigation.provenance import (
    InvestigationProvenance,
)

from sentinel_dna.investigation.replay import (
    InvestigationReplay,
)

from sentinel_dna.investigation.planning import (
    InvestigationPlanner,
)

from sentinel_dna.investigation.reporting import (
    InvestigationReporter,
)

from sentinel_dna.investigation.result import (
    InvestigationResult,
)

from sentinel_dna.investigation.storage.lineage_store import (
    InvestigationLineageStore,
)

from sentinel_dna.investigation.trace_manager import (
    attach_trace,
)

from sentinel_dna.risk.risk_engine import (
    RiskEngine,
)

from sentinel_dna.services.intelligence.fusion.evidence_fusion import (
    EvidenceFusionEngine,
)
from sentinel_dna.investigation.graph_insights import GraphInsightsEngine
from sentinel_dna.investigation.response import ResponseRecommendationEngine
from sentinel_dna.investigation.detection import DetectionRecommendationEngine
from .runtime import (
    RuntimeTask,
    RuntimeTaskExecutor,
)


class InvestigationOrchestrator:
    """
    Canonical Sentinel DNA investigation workflow engine.

    Enterprise investigation lifecycle:

        Alert
          |
          v
    Investigation Context
          |
          v
    Evidence Collection
          |
          v
    IOC Intelligence
          |
          v
    Entity Correlation
          |
          v
    Threat Analysis
          |
          v
    Risk + Confidence
          |
          v
    AI Reasoning
          |
          v
    Decision Intelligence
          |
          v
    Report + Lineage


    Maintains compatibility with:

    - AI Investigator v1
    - Telemetry Gateway
    - InvestigationResult contract
    - Existing tests
    """


    def __init__(
        self,
        data_dir: str | Path = "data",
        runtime: RuntimeTaskExecutor | None = None,
        planner: InvestigationPlanner | None = None,
        reporter: InvestigationReporter | None = None,
    ) -> None:
        self.case_store = CaseStore(
            data_dir
        )

        self.evidence_engine = EvidenceEngine(
            data_dir
        )

        self.risk_engine = RiskEngine()

        self.fusion_engine = EvidenceFusionEngine()
        self.graph_insights_engine = GraphInsightsEngine()
        self.response_engine = ResponseRecommendationEngine()
        self.detection_engine = DetectionRecommendationEngine()

        self.reporter = (
            reporter
            or InvestigationReporter()
        )

        # Public compatibility contract
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

        self.lineage_store = (
            InvestigationLineageStore(
                data_dir
            )
        )


    def run(
        self,
        context: InvestigationContext,
    ) -> InvestigationResult:
        """
        Execute the complete investigation workflow.

        The orchestrator owns workflow coordination while the
        planner defines the investigation stages and the runtime
        executes them.
        """

        if context.trace is None:
            attach_trace(context)

        self._initialize_lineage(context)

        plan = self.planner.create_plan(
            context,
            self,
        )

        self.runtime.execute(
            context,
            plan,
        )

        results = self._assemble_results(
            context,
            plan,
        )

        if context.trace:
            results["audit_trail"] = context.trace.events

        self.lineage_store.save_context_lineage(
            context
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

            context.provenance = (
                InvestigationProvenance(
                    context.case_id
                )
            )


        if context.replay is None:

            context.replay = (
                InvestigationReplay(
                    context.case_id
                )
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

        self._record_replay(
            context,
            stage=stage,
            message=f"{action} recorded from {source}",
            details=details,
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
            or "Security Alert"
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
                "alert": alert,
            },
        )

        self.case_store.save(
            case
        )

        context.alert = alert
        context.case = case
        context.graph.add_node(
            "alert", context.case_id,
            metadata={"severity": severity, "title": title},
        )

        self._record_provenance(
            context,
            stage="context",
            action="case_loaded",
            source="CaseStore",
            details={
                "case_id": context.case_id,
            },
        )


    def collect_evidence(
        self,
        context: InvestigationContext,
    ) -> None:

        evidence = (
            self.evidence_engine.normalize_email(
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


        if context.case:

            context.case.attach_evidence(
                evidence.evidence_id
            )

            self.case_store.save(
                context.case
            )


        if not context.iocs:

            context.uncertainties.append(
                "No IOCs were discovered in the submitted alert evidence."
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


    def enrich_iocs(
        self,
        context: InvestigationContext,
    ) -> None:

        enriched = {}


        for ioc in context.iocs:

            normalized = ioc.lower()


            indicator_type = (
                "url"
                if normalized.startswith(
                    (
                        "http://",
                        "https://",
                    )
                )
                else
                "email_or_domain"
            )


            reputation = (
                "suspicious"
                if any(
                    keyword in normalized
                    for keyword in (
                        "login",
                        "verify",
                        "password",
                        "credential",
                    )
                )
                else
                "unknown"
            )


            enriched[ioc] = {

                "indicator": ioc,

                "type": indicator_type,

                "source": "local_rules",

                "reputation": reputation,
            }

            if "." in normalized:
                domain = normalized.split("/")[2] if "://" in normalized else normalized
                context.graph.add_node("domain", domain, metadata={"source_ioc": ioc})


        context.intelligence["iocs"] = enriched


        self._record_provenance(
            context,
            stage="intelligence",
            action="ioc_enrichment_completed",
            source="LocalIOCAnalyzer",
            details={
                "ioc_count": len(enriched),
            },
        )


    def evaluate_threat_intelligence(
        self,
        context: InvestigationContext,
    ) -> None:

        suspicious = [

            ioc

            for ioc, intelligence
            in context.intelligence.get(
                "iocs",
                {},
            ).items()

            if intelligence.get(
                "reputation"
            )
            == "suspicious"

        ]


        context.intelligence["threat"] = {

            "source": "local_rules",

            "suspicious_iocs": suspicious,

            "summary":
                (
                    "Suspicious indicators identified."
                    if suspicious
                    else
                    "No suspicious indicators identified."
                ),
        }


        self._record_provenance(
            context,
            stage="intelligence",
            action="threat_intelligence_completed",
            source="LocalThreatAnalyzer",
            details={
                "suspicious_count": len(suspicious),
            },
        )

    def correlate_entities(
        self,
        context: InvestigationContext,
    ) -> None:

        correlations = []

        for evidence in context.evidence_items:

            evidence_node = (
                context.graph.add_node(
                    "evidence",
                    evidence.evidence_id,
                    metadata={"source": evidence.evidence_type, "confidence": evidence.confidence},
                )
            )

            for ioc in evidence.indicators:

                ioc_node = (
                    context.graph.add_node(
                        "ioc",
                        ioc,
                        metadata={"indicator": ioc},
                    )
                )

                context.graph.add_edge(
                    evidence_node,
                    ioc_node,
                    "contains",
                    metadata={"source": "EvidenceEngine"},
                    confidence=evidence.confidence,
                    lineage=[evidence.evidence_id],
                )

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
                "No event or entity correlations established."
            )

    def analyze_graph(self, context: InvestigationContext) -> None:
        """Enrich the evidence graph with threat mappings and calculate graph intelligence."""
        for mapping in context.mitre_attack:
            technique = context.graph.add_node(
                "mitre_attack_technique", mapping["technique_id"],
                metadata={"technique": mapping["technique"]},
            )
            for ioc_node in [node for node in context.graph.nodes.values() if node.node_type == "ioc"]:
                context.graph.add_edge(ioc_node, technique, "maps_to", confidence=0.8,
                                       lineage=context.graph.evidence_lineage(ioc_node))
        context.graph_insights = self.graph_insights_engine.analyze(context.graph)


    def fuse_evidence(
        self,
        context: InvestigationContext,
    ) -> None:
        """
        Fuse evidence, IOC intelligence, graph correlations, and MITRE mappings
        before risk and confidence are calculated.
        """

        context.fusion = self.fusion_engine.fuse(context)

        context.intelligence["fusion"] = context.fusion.to_dict()

        fusion_node = context.graph.add_node(
            "fusion_verdict",
            context.fusion.verdict,
            metadata={
                "confidence": context.fusion.confidence,
                "sources": context.fusion.contributing_sources,
                "evidence_count": context.fusion.evidence_count,
            },
        )

        for evidence in context.evidence_items:
            evidence_node = context.graph.add_node(
                "evidence",
                evidence.evidence_id,
                metadata={"source": evidence.evidence_type, "confidence": evidence.confidence},
            )
            context.graph.add_edge(
                evidence_node,
                fusion_node,
                "contributes_to",
                metadata={"source": "EvidenceFusionEngine"},
                confidence=evidence.confidence,
                lineage=[evidence.evidence_id],
            )

        self._record_provenance(
            context,
            stage="fusion",
            action="evidence_fused",
            source="EvidenceFusionEngine",
            details={
                "verdict": context.fusion.verdict,
                "confidence": context.fusion.confidence,
                "sources": context.fusion.contributing_sources,
            },
            confidence=context.fusion.confidence,
        )


    def build_timeline(
        self,
        context: InvestigationContext,
    ) -> None:

        context.timeline = [

            {
                "timestamp":
                    evidence.observed_at,

                "event":
                    evidence.summary,

                "evidence_id":
                    evidence.evidence_id,
            }

            for evidence in sorted(
                context.evidence_items,
                key=lambda item: item.observed_at,
            )

        ]


    def map_mitre_attack(
        self,
        context: InvestigationContext,
    ) -> None:

        text = self._evidence_text(
            context
        ).lower()


        mappings = []


        if any(
            keyword in text

            for keyword in (
                "password",
                "credential",
                "verify",
                "login",
                "mfa",
                "account",
            )

        ):

            mappings.append(
                {
                    "technique_id":
                        "T1566",

                    "technique":
                        "Phishing",

                    "evidence":
                        "Credential phishing indicators detected.",
                }
            )


        if any(
            keyword in text

            for keyword in (
                "invoice",
                "wire",
                "payment",
                "bank",
            )

        ):

            mappings.append(
                {
                    "technique_id":
                        "T1657",

                    "technique":
                        "Financial Theft",

                    "evidence":
                        "Payment-related indicators detected.",
                }
            )


        context.mitre_attack = mappings

        # Keep direct callers of this stage supplied with current graph intelligence.
        self.analyze_graph(context)



    def classify_threat(
        self,
        context: InvestigationContext,
    ) -> None:


        techniques = [

            item["technique"]

            for item in context.mitre_attack

        ]


        context.threat_classification = {

            "classification":
                (
                    "phishing"
                    if "Phishing" in techniques
                    else "unknown"
                ),

            "mapped_techniques":
                techniques,
        }



    def calculate_risk(
        self,
        context: InvestigationContext,
    ) -> None:


        context.risk = (
            self.risk_engine.assess(context.evidence_items, context.intelligence,
                                    context.mitre_attack, context.graph_insights,
                                    context.uncertainties, context.fusion)
        )

        context.graph.add_node(
            "risk_signal", context.risk.level,
            metadata={"score": context.risk.score, "reasons": context.risk.reasons},
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
                    item.confidence
                    for item in context.evidence_items
                )

                /

                len(
                    context.evidence_items
                )

            )


            if context.errors:

                score -= 0.15


            if context.uncertainties:

                score -= 0.10



        context.confidence = {

            "score":

                round(
                    max(
                        0.0,
                        min(
                            1.0,
                            score,
                        ),
                    ),
                    2,
                ),


            "basis":
                "Evidence confidence, IOC intelligence quality, graph relationships, and investigation uncertainty.",

            "factors": [
                {"name": "evidence_confidence", "score": round(sum(item.confidence for item in context.evidence_items) / len(context.evidence_items), 2) if context.evidence_items else 0.0},
                {"name": "ioc_intelligence_quality", "score": 1.0 if context.intelligence.get("threat", {}).get("suspicious_iocs") else 0.5},
                {"name": "graph_relationship_confidence", "score": round(sum(edge.confidence for edge in context.graph.edges) / len(context.graph.edges), 2) if context.graph.edges else 0.0},
            ],


            "uncertainties":
                list(
                    dict.fromkeys(
                        context.uncertainties
                    )
                ),

        }



    def perform_reasoning(
        self,
        context: InvestigationContext,
    ) -> None:


        findings = []


        for evidence in context.evidence_items:

            findings.append(
                {
                    "claim":
                        evidence.summary,

                    "evidence_id":
                        evidence.evidence_id,

                    "confidence":
                        evidence.confidence,
                    "supporting_evidence": [{"artifact": evidence.evidence_type, "indicator": indicator,
                                               "confidence": evidence.confidence} for indicator in evidence.indicators],
                    "reasoning_factors": ["Evidence normalized and correlated", "IOC relationship recorded"],
                }
            )


        context.reasoning = {

            "mode":
                "evidence_grounded_rules",


            "findings":
                findings,


            "conclusion":
                self._conclusion(
                    context
                ),
            "trace": {
                "finding": self._conclusion(context),
                "supporting_evidence": [item for finding in findings for item in finding["supporting_evidence"]],
                "reasoning": ["Evidence confidence evaluated", "Graph relationships analyzed",
                              "MITRE techniques mapped" if context.mitre_attack else "No MITRE technique mapped"],
                "decision": "Escalate investigation" if context.risk and context.risk.level in {"high", "critical"} else "Monitor investigation",
            },
        }


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

            "risk_level":
                risk_level,

            "confidence_score":
                context.confidence.get(
                    "score",
                    0.0,
                ),

            "recommended_decision":

                (
                    "escalate"

                    if risk_level in {
                        "critical",
                        "high",
                    }

                    else

                    "monitor"
                ),

            "rationale":

                context.reasoning.get(
                    "conclusion",
                    "",
                ),
        }

        decision = context.graph.add_node(
            "investigation_decision",
            context.decision_intelligence["recommended_decision"],
            metadata={"confidence": context.decision_intelligence["confidence_score"]},
        )
        for risk_node in [node for node in context.graph.nodes.values() if node.node_type == "risk_signal"]:
            context.graph.add_edge(
                risk_node, decision, "supports",
                confidence=context.confidence.get("score", 0.0),
            )
        context.graph_insights = self.graph_insights_engine.analyze(context.graph)



    def produce_recommendations(
        self,
        context: InvestigationContext,
    ) -> None:

        if context.recommendations:
            return

        if not context.iocs:
            risk_level = "low"
        else:
            risk_level = (
                context.risk.level
                if context.risk
                else "low"
            )

        context.recommendations = (
            self.investigation_engine
            .recommend_actions(
                risk_level
            )
        )

    def generate_response_recommendations(self, context: InvestigationContext) -> None:
        context.response_recommendations = self.response_engine.recommend(context)

    def generate_detection_recommendations(self, context: InvestigationContext) -> None:
        context.detection_recommendations = self.detection_engine.generate(context)


    def generate_report(
        self,
        context: InvestigationContext,
    ) -> None:


        if (
            context.case is None
            or context.risk is None
        ):

            context.report = {

                "status":
                    "incomplete",

                "reason":
                    "Missing case or risk assessment.",
            }

            return



        summary = (

            self.investigation_engine
            .summarize(
                context.case,
                context.evidence_items,
                context.risk,
                recommended_actions=
                    context.recommendations,
            )

        )


        context.report = {

            "executive_summary":
                summary.executive_summary,


            "key_findings":
                summary.key_findings,


            "recommended_actions":
                summary.recommended_actions,


            "confidence_statement":
                summary.confidence_statement,

            "investigation_overview": {
                "case_id": context.case_id,
                "alert_source": context.alert.get("source", "submitted_alert"),
                "timestamps": {"created_at": context.case.created_at, "updated_at": context.case.updated_at},
                "severity": context.case.severity,
            },
            "attack_narrative": context.reasoning.get("conclusion", "No supported attack narrative available."),
            "response_recommendations": context.response_recommendations,
            "detection_recommendations": context.detection_recommendations,
            "audit_trail": context.audit_trail,
            "format_version": "1.0",

            "evidence_findings": context.reasoning.get("findings", []),
            "graph_relationships": context.graph.to_dict().get("edges", []),
            "mitre_mappings": context.mitre_attack,
            "risk_explanation": context.risk.reasons,
            "confidence_explanation": context.confidence,

        }



    def _assemble_results(
        self,
        context: InvestigationContext,
        plan: list[RuntimeTask],
    ) -> dict[str, Any]:


        return {

            "investigation": {

                "case_id":
                    context.case_id,


                "plan_name":
                    self.planner.plan_name,


                "status":
                    (
                        "completed_with_errors"

                        if context.errors

                        else

                        "completed"
                    ),
            },


            "case_id":
                context.case_id,


            "alert":
                context.alert,


            "plan": {

                "name":
                    self.planner.plan_name,


                "tasks":
                    [
                        task.name
                        for task in plan
                    ],
            },


            "tasks":
                context.task_results,


            "evidence":

                [
                    vars(item)
                    for item in context.evidence_items
                ],


            "graph":

                (
                    context.graph.to_dict()

                    if context.graph

                    else {}
                ),

            "graph_insights": context.graph_insights or {},


            "provenance":

                (
                    context.provenance.to_dict()

                    if context.provenance

                    else {}
                ),


            "replay":

                (
                    context.replay.to_dict()

                    if context.replay

                    else {}
                ),


            "iocs":

                context.iocs or [],


            "intelligence":

                context.intelligence or {},


     "mitre_attack":
         context.mitre_attack or [],


     "threat_classification":
         context.threat_classification or {},


     "correlations":
        context.correlations or [],


            "timeline":
                context.timeline or [],


            "risk":

                (
                    vars(context.risk)

                    if context.risk

                    else None
                ),


            "confidence":
                context.confidence or {},


            "reasoning":
                context.reasoning or {},
             "fusion":
                 (
                      context.fusion.to_dict()
                      if context.fusion
                      else {}
                 ),


            "decision_intelligence":
                context.decision_intelligence or {},


            "recommendations":
                context.recommendations or [],

            "response_recommendations":
                context.response_recommendations or [],

            "detection_recommendations":
                context.detection_recommendations or [],


            "report":
                context.report or {},


            "uncertainties":

                list(
                    dict.fromkeys(
                        context.uncertainties
                    )
                ),
        }



    def _evidence_text(
        self,
        context: InvestigationContext,
    ) -> str:


        content = []


        for evidence in context.evidence_items:

            content.append(
                str(
                    getattr(
                        evidence,
                        "summary",
                        "",
                    )
                )
            )


            content.append(
                str(
                    getattr(
                        evidence,
                        "content",
                        "",
                    )
                )
            )


        return " ".join(
            content
        )



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

            str(key):
                value

            for key, value in alert.items()

        }
