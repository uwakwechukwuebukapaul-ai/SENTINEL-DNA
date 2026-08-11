from sentinel_dna.investigation.context import InvestigationContext
from sentinel_dna.investigation.runtime import RuntimeTask


class InvestigationPlanner:
    plan_name = "ai-investigator-v1"

    def create_plan(self, context: InvestigationContext, orchestrator: object) -> list[RuntimeTask]:
        return [
            RuntimeTask("load_context", orchestrator.load_context, required=True),
            RuntimeTask("collect_evidence", orchestrator.collect_evidence, required=True),
            RuntimeTask("enrich_iocs", orchestrator.enrich_iocs),
            RuntimeTask("correlate_entities", orchestrator.correlate_entities),
            RuntimeTask("build_timeline", orchestrator.build_timeline),
            RuntimeTask("evaluate_threat_intelligence", orchestrator.evaluate_threat_intelligence),
            RuntimeTask("map_mitre_attack", orchestrator.map_mitre_attack),
            RuntimeTask("classify_threat", orchestrator.classify_threat),
            RuntimeTask("calculate_risk", orchestrator.calculate_risk),
            RuntimeTask("calculate_confidence", orchestrator.calculate_confidence),
            RuntimeTask("perform_reasoning", orchestrator.perform_reasoning),
            RuntimeTask("generate_decision_intelligence", orchestrator.generate_decision_intelligence),
            RuntimeTask("produce_recommendations", orchestrator.produce_recommendations),
            RuntimeTask("generate_report", orchestrator.generate_report),
        ]
