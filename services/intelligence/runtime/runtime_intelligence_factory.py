"""
Runtime Intelligence Factory

Creates configured intelligence runtime.
"""


from services.intelligence.runtime.runtime_intelligence_service import (
    RuntimeIntelligenceService,
)

from services.intelligence.runtime.runtime_intelligence_controller import (
    RuntimeIntelligenceController,
)

from services.intelligence.runtime.runtime_intelligence_pipeline import (
    RuntimeIntelligencePipeline,
)

from services.intelligence.runtime.runtime_investigation_bridge import (
    RuntimeInvestigationBridge,
)



class RuntimeIntelligenceFactory:


    @staticmethod
    def create(
        providers=None,
        correlation_engine=None,
        fusion_engine=None,
    ):


        service = RuntimeIntelligenceService(
            providers=providers,
            correlation_engine=correlation_engine,
            fusion_engine=fusion_engine,
        )


        pipeline = RuntimeIntelligencePipeline(
            service
        )


        controller = RuntimeIntelligenceController(
            service
        )


        bridge = RuntimeInvestigationBridge(
            service
        )


        return {
            "service": service,
            "pipeline": pipeline,
            "controller": controller,
            "bridge": bridge,
        }