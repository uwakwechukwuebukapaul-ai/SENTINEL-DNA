import json
from services.billing.service import BillingService
from services.detection import DetectionEngine
from services.telemetry import EventNormalizer
from services.forensics import ForensicsService
from services.governance import GovernanceService
from services.intelligence.reasoning.autonomous import AutonomousInvestigationEngine

def test_billing_quota_and_tiers():
    billing = BillingService(); billing.configure("org-a", "trial"); billing.consume("org-a", "events", 10); assert billing.status("org-a")["usage"]["events"] == 10
    try: billing.consume("org-a", "events", 10000); assert False
    except PermissionError: pass

def test_detection_dataset_signal():
    event = EventNormalizer().normalize({"event_type": "process_creation", "message": "powershell -enc payload"}, "windows")
    assert any(alert.technique_id == "T1059.001" for alert in DetectionEngine().process(event))

def test_forensics_hash_and_tenant_export():
    service = ForensicsService(); evidence = service.add_evidence("org-a", "case-1", {"x": 1}, 7); assert len(evidence["sha256"]) == 64; assert service.export(evidence["id"], "org-a")["chain_of_custody"]

def test_governance_approval():
    service = GovernanceService(); approval = service.request_approval("org-a", "contain", "decision-1"); assert service.approve(approval["id"], "approved")["status"] == "approved"

def test_autonomous_reasoning_is_explainable():
    result = AutonomousInvestigationEngine().investigate("org-a", {"techniques": ["T1059.001"]}, [{"type": "process"}], ["ioc"])
    assert {"evidence", "reasoning", "confidence", "recommended_action"}.issubset(result["decision"])
