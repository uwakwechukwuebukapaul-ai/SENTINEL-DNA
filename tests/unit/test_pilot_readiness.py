from services.monitoring import MonitoringService
from services.forensics import ForensicsService
from services.tenancy.service import TenancyService
from deployment.upgrades import UpgradeManager
def test_monitoring_latency_snapshot():
    service = MonitoringService(); service.record_latency("detection", 10); service.record_latency("detection", 20); assert service.snapshot()["detection_latency_ms"]["average_ms"] == 15
def test_tenant_evidence_isolation():
    service = ForensicsService(); item = service.add_evidence("org-a", "case", {"x": 1}, 1)
    try: service.export(item["id"], "org-b"); assert False
    except LookupError: pass
def test_upgrade_rollback_readiness():
    manager = UpgradeManager(); assert manager.apply("1.1.0", ["001_add_index"])["rollback_ready"]; assert manager.rollback()["status"] == "rollback_ready"
def test_tenant_membership_isolation():
    service = TenancyService(); org = service.create("Pilot", owner_id=1); assert service.role(org.organization_id, 1) == "admin"; assert service.role(org.organization_id, 2) is None
