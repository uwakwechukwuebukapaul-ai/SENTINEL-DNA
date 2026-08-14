from services.integrations.connector import BaseConnector
from services.integrations.credentials import CredentialManager
from services.integrations.service import IntegrationService
from services.integrations.connectors import SyntheticSIEMConnector,SyntheticThreatIntelConnector,SyntheticTicketConnector,SyntheticWebhookConnector
def test_connector_registration(): s=IntegrationService(); c=type("C",(BaseConnector,),{"connector_id":"c"})(); assert s.register(c).connector_id == "c"
def test_connector_health(): s=IntegrationService(); c=type("C",(BaseConnector,),{"connector_id":"c"})(); s.register(c); assert s.test_connection("c")["status"] == "healthy"
def test_credential_masking(): c=CredentialManager(); c.store("x","c","api_key","vault://x"); assert c.get_masked("x")["encrypted_reference"] == "***"
def test_no_secret_serialization(): c=CredentialManager(); c.store("x","c","api_key","vault://x"); assert "secret" not in str(c.get_masked("x")).lower()
def test_synthetic_siem_connector(): assert SyntheticSIEMConnector().receive()["synthetic_only"]
def test_threat_intel_connector(): assert SyntheticThreatIntelConnector().lookup("x")["matches"] == []
def test_ticket_connector(): assert SyntheticTicketConnector().create_ticket("x")["ticket_reference"]
def test_webhook_connector(): assert SyntheticWebhookConnector().send({})["accepted"]
def test_audit_logging(): s=IntegrationService(); c=type("C",(BaseConnector,),{"connector_id":"c"})(); s.register(c); assert s.audit.events
def test_deterministic_behavior(): assert SyntheticTicketConnector().create_ticket("x")["ticket_reference"] == "SYNTH-1"
