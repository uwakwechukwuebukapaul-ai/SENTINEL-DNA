"""
Sentinel DNA Agent Bootstrap

Registers enterprise AI investigation agents.
"""

from services.intelligence.agents.investigation_agent import (
    InvestigationAgent,
)

from services.intelligence.agents.threat_intelligence_agent import (
    ThreatIntelligenceAgent,
)

from services.intelligence.agents.ioc_enrichment_agent import (
    IOCEnrichmentAgent,
)


def bootstrap_agents(
    registry,
    runtime_adapter=None,
):
    """
    Register all intelligence agents.
    """

    agents = [
        InvestigationAgent(),
        ThreatIntelligenceAgent(),
        IOCEnrichmentAgent(),
    ]


    for agent in agents:

        registry.register(
            agent
        )

        if runtime_adapter:

            runtime_adapter.register_agent(
                agent
            )


    return registry