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
    assert finding.evidence_status == "attached"


def test_reasoner_does_not_fabricate_evidence_references():
    context = InvestigationContext("CASE-2", {"objective": "investigate phishing"})
    context.add_evidence({"description": "Suspicious email with phishing indicators"})
    finding = EvidenceReasoner().reason(context).findings[0]
    assert finding.evidence_refs == []
    assert finding.evidence_status == "not_attached"


def test_reasoner_preserves_multiple_references_and_serialization():
    context = InvestigationContext("CASE-3", {"objective": "investigate phishing"})
    context.add_evidence({"evidence_id": "E-1", "description": "phishing email"})
    context.add_evidence({"artifact_id": "A-1", "description": "credential prompt"})
    finding = EvidenceReasoner().reason(context).findings[0]
    assert finding.evidence_refs == ["E-1", "A-1"]
    assert finding.to_dict()["evidence_refs"] == ["E-1", "A-1"]
    assert finding.to_dict()["evidence_status"] == "attached"


def test_reasoner_omits_cross_tenant_evidence_reference():
    context = InvestigationContext("CASE-4", {"objective": "investigate phishing"})
    context.tenant_id = "tenant-a"
    context.add_evidence({"evidence_id": "E-A", "tenant_id": "tenant-a", "description": "phishing email"})
    context.add_evidence({"evidence_id": "E-B", "tenant_id": "tenant-b", "description": "credential prompt"})
    finding = EvidenceReasoner().reason(context).findings[0]
    assert finding.evidence_refs == ["E-A"]
    assert finding.evidence_status == "attached"
    assert "E-B" not in finding.to_dict()["evidence_refs"]


def test_reasoner_marks_only_cross_tenant_reference_not_attached():
    context = InvestigationContext("CASE-5", {"objective": "investigate phishing"})
    context.tenant_id = "tenant-a"
    context.add_evidence({"evidence_id": "E-B", "tenant_id": "tenant-b", "description": "credential prompt"})
    finding = EvidenceReasoner().reason(context).findings[0]
    assert finding.evidence_refs == []
    assert finding.evidence_status == "not_attached"


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
