from copy import deepcopy

from services.intelligence.ai_runtime import AIRuntimeService, DeterministicMockProvider
from services.intelligence.context.investigation_context import InvestigationContext
from services.intelligence.reasoning import EvidenceReasoner


def _context():
    context = InvestigationContext("CASE-1", {"objective": "investigate phishing"})
    context.add_evidence({"evidence_id": "E-1", "description": "Suspicious email with phishing indicators"})
    context.add_ioc({"id": "IOC-1", "type": "url", "value": "malicious URL"})
    context.add_timeline_event({"id": "T-1", "event": "email received"})
    return context


def test_reasoner_generates_findings():
    report = EvidenceReasoner().reason(_context())
    assert report.findings[0].title == "Potential Credential Harvesting Attempt"


def test_reasoner_links_evidence():
    finding = EvidenceReasoner().reason(_context()).findings[0]
    assert finding.evidence_refs == ["E-1"]


def test_reasoner_maps_mitre():
    finding = EvidenceReasoner().reason(_context()).findings[0]
    assert "T1566" in finding.mitre_techniques


def test_reasoner_confidence():
    report = EvidenceReasoner().reason(_context())
    assert report.confidence == 0.88


def test_reasoner_does_not_mutate_context():
    context = _context()
    before = deepcopy(context.snapshot())
    EvidenceReasoner().reason(context)
    assert context.snapshot() == before


def test_ai_runtime_reasoning_integration():
    runtime = AIRuntimeService(DeterministicMockProvider())
    report = EvidenceReasoner(runtime).reason(_context())
    assert report.metadata["provider"] == "deterministic_mock"
    assert report.metadata["synthetic_only"] is True
    assert report.metadata["ai_evidence_references"] == ["E-1"]
    assert "required_reasoning_task" in report.metadata["prompt"]
