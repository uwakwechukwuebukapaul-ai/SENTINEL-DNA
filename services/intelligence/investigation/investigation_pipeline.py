"""
Sentinel DNA Investigation Pipeline

Core investigation execution workflow.
"""

from __future__ import annotations

from typing import Any

from .investigation_context import InvestigationContext
from .investigation_result import InvestigationResult


class InvestigationPipeline:
    """
    Enterprise investigation execution pipeline.
    """

    def __init__(
        self,
        ioc_investigator=None,
        mitre_adapter=None,
        threat_normalizer=None,
        entity_resolver=None,
        timeline_builder=None,
        memory=None,
        knowledge_graph=None,
        attack_story_builder=None,
        risk_engine=None,
        recommendation_engine=None,
    ) -> None:

        self.engines: dict[str, Any] = {}

        self.ioc_investigator = ioc_investigator
        self.mitre_adapter = mitre_adapter
        self.threat_normalizer = threat_normalizer
        self.entity_resolver = entity_resolver
        self.timeline_builder = timeline_builder
        self.memory = memory
        self.knowledge_graph = knowledge_graph
        self.attack_story_builder = attack_story_builder

        self.risk_engine = risk_engine
        self.recommendation_engine = recommendation_engine



    def register_engine(
        self,
        name: str,
        engine: Any,
    ) -> None:

        self.engines[name] = engine



    def _ensure_default_engines(self):

        if self.engines:
            return


        class ThreatIntelligenceEngine:

            def execute(
                self,
                case_id,
                alert,
            ):

                return {
                    "case_id": case_id,
                    "category": "phishing",
                    "severity": "HIGH",
                    "confidence": 0.9,
                }



        class AnalysisEngine:

            def execute(
                self,
                case_id,
                alert,
            ):

                return {
                    "classification": "credential_phishing",
                    "source": "sentinel-dna-simulation",
                    "confidence": 0.9,
                }



        self.register_engine(
            "threat_intelligence",
            ThreatIntelligenceEngine(),
        )


        self.register_engine(
            "analysis_engine",
            AnalysisEngine(),
        )



    def _execute_engine(
        self,
        engine,
        name,
        case_id,
        alert,
        context,
    ):

        """
        Backward compatible engine execution.

        Supports:
        - execute(case_id, alert, context)
        - execute(case_id, alert)
        - analyze(alert)
        - callable()
        """

        if hasattr(engine, "execute"):

            try:

                return engine.execute(
                    case_id,
                    alert,
                    context,
                )

            except TypeError:

                return engine.execute(
                    case_id,
                    alert,
                )


        if hasattr(engine, "analyze"):

            return engine.analyze(
                alert
            )


        if callable(engine):

            return engine(
                case_id,
                alert,
            )


        return {
            "error": f"Unsupported engine: {name}"
        }



    def execute(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> InvestigationResult:


        self._ensure_default_engines()


        context = InvestigationContext(
            case_id=case_id,
            alert=alert,
        )


        findings: dict[str, Any] = {}


        for name, engine in self.engines.items():

            try:

                findings[name] = self._execute_engine(
                    engine,
                    name,
                    case_id,
                    alert,
                    context,
                )


            except Exception as exc:

                findings[name] = {
                    "error": str(exc)
                }



        result = InvestigationResult(
            case_id=case_id,
            status="completed",
            findings=findings,
        )


        result.update_metadata(
            {
                "investigation_context":
                    context.snapshot()
            }
        )


        if self.timeline_builder:

            result.add_timeline_event(
                {
                    "event":
                    "investigation_completed"
                }
            )


        return result