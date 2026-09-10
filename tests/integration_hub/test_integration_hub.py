from services.integration_hub import *
from services.integration_hub.service import IntegrationHubService
from tests.credential_helpers import random_token
def test_registration_validation_and_health():
    token = random_token()
    service = IntegrationHubService(); c = service.register("t1", "SIEM", ConnectorType.SIEM, "synthetic", credentials={"token": token})
    assert service.validate(c.connector_id, "t1") and service.check_health(c.connector_id, "t1").status == "healthy"
    assert token not in str(c.to_dict())
def test_tenant_isolation():
    service = IntegrationHubService(); c = service.register("t1", "EDR", ConnectorType.EDR, "synthetic")
    assert service.get(c.connector_id, "t2") is None and service.list("t2") == []
def test_event_routing_and_disable():
    service = IntegrationHubService(); c = service.register("t1", "Cloud", ConnectorType.CLOUD, "synthetic"); service.validate(c.connector_id, "t1")
    assert service.route_event("t1", c.connector_id, "telemetry", "ref").tenant_id == "t1"
    service.disable(c.connector_id, "t1")
    try: service.route_event("t1", c.connector_id, "telemetry", "ref")
    except PermissionError: pass
    else: assert False
