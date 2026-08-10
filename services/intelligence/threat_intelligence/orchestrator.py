"""
Threat Intelligence Orchestrator.

Coordinates enrichment workflow.
"""

from services.intelligence.threat_intelligence.ioc_extractor import (
    IOCExtractor,
)

from services.intelligence.threat_intelligence.reputation_engine import (
    ReputationEngine,
)

from services.intelligence.threat_intelligence.mitre_mapper import (
    MITREMapper,
)

from services.intelligence.threat_intelligence.enrichment_result import (
    ThreatIntelligenceResult,
)



class ThreatIntelligenceOrchestrator:


    def __init__(
        self,
        ioc_extractor=None,
        reputation_engine=None,
        mitre_mapper=None,
    ):


        self.ioc_extractor = (
            ioc_extractor
            or IOCExtractor()
        )


        self.reputation_engine = (
            reputation_engine
            or ReputationEngine()
        )


        self.mitre_mapper = (
            mitre_mapper
            or MITREMapper()
        )



    def enrich(
        self,
        investigation,
    ):


        artifacts = investigation.get(
            "artifacts",
            [],
        )


        threat = investigation.get(
            "threat",
            "unknown",
        )


        iocs = (
            self.ioc_extractor.extract(
                artifacts
            )
        )


        reputation = (
            self.reputation_engine.analyze(
                iocs
            )
        )


        mitre = (
            self.mitre_mapper.map(
                threat
            )
        )


        result = ThreatIntelligenceResult(

            iocs=iocs,

            reputation=reputation,

            mitre_attack=mitre,

            threat_profile={
                "threat":
                    threat,
            },

            metadata={
                "enrichment_status":
                    "completed",
            },

        )


        return result.to_dict()