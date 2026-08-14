"""Regression tests for case context propagation into investigation agents."""

from services.intelligence.agents.runtime_adapter import AgentRuntimeAdapter
from services.intelligence.agents.ioc_enrichment_agent import IOCEnrichmentAgent
from services.intelligence.agents.threat_intelligence_agent import (
    ThreatIntelligenceAgent,
)
from services.intelligence.orchestration.investigation_coordinator import (
    InvestigationCoordinator,
)


def test_coordinator_context_and_task_keep_case_collections():
    coordinator = InvestigationCoordinator()
    evidence = [{"type": "LOG FILE", "data": "security event log"}]
    iocs = [{"type": "IP ADDRESS", "value": "185.22.45.100"}]
    timeline = [{"event_type": "ALERT", "description": "IOC observed"}]

    context = coordinator.create_context(
        "CASE-001",
        artifacts=evidence,
        evidence=evidence,
        iocs=iocs,
        timeline=timeline,
    )
    task = coordinator._create_runtime_task(
        "CASE-001",
        {"case_id": "CASE-001"},
        coordinator.create_plan("CASE-001", {}),
        "ioc_enrichment",
        context,
    )

    assert context.evidence == evidence
    assert context.iocs == iocs
    assert context.timeline == timeline
    assert task.payload["evidence"] == evidence
    assert task.payload["iocs"] == iocs
    assert task.payload["timeline"] == timeline


def test_agent_context_passes_iocs_and_evidence_to_both_agents():
    coordinator = InvestigationCoordinator()
    context = coordinator.create_context(
        "CASE-001",
        artifacts=[{"type": "LOG FILE", "data": "event log"}],
        evidence=[{"type": "LOG FILE", "data": "event log"}],
        iocs=[
            {"type": "IP ADDRESS", "value": "185.22.45.100"},
            {"type": "DOMAIN", "value": "malicious-example.xyz"},
        ],
        timeline=[{"event_type": "ALERT"}],
    )
    payload = {
        "case_id": "CASE-001",
        "alert": {"case_id": "CASE-001"},
        "context": context,
    }
    agent_context = AgentRuntimeAdapter(None)._build_agent_context(payload)

    assert agent_context.iocs == [
        "185.22.45.100",
        "malicious-example.xyz",
    ]
    assert agent_context.evidence == context.evidence
    assert agent_context.timeline == context.timeline

    enrichment = IOCEnrichmentAgent().execute(agent_context)
    assessment = ThreatIntelligenceAgent().execute(agent_context)

    assert enrichment.metadata["ioc_count"] == 2
    assert assessment.metadata["assessment_count"] == 2
