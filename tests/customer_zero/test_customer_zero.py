from lab.customer_zero.organization import ORGANIZATION
from lab.customer_zero.assets import ASSETS
from lab.customer_zero.telemetry_generator import TelemetryGenerator
from lab.customer_zero.runner import CustomerZeroRunner
def test_customer_zero_organization_and_assets():
    assert ORGANIZATION["name"] == "Sentinel Finance Demo"; assert {x["hostname"] for x in ASSETS} >= {"FIN-WIN-001", "FIN-LINUX-001", "AWS-PROD-001"}
def test_telemetry_is_tenant_scoped():
    events = TelemetryGenerator(ORGANIZATION["organization_id"]).scenario("credential_attack"); assert events and all(x["organization_id"] == ORGANIZATION["organization_id"] for x in events)
def test_customer_zero_run_generates_detection_and_score():
    result = CustomerZeroRunner().run("credential_attack"); assert result["detections"]; assert result["metrics"]["overall_score"] == 97; assert result["progress"] == 100
def test_unknown_scenario_rejected():
    try: CustomerZeroRunner().run("unknown")
    except ValueError: return
    assert False
