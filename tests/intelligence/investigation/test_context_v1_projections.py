from services.intelligence.investigation.context_v1 import InvestigationContextV1


def _context():
    return InvestigationContextV1(
        investigation_id="CASE-1",
        tenant_id="TENANT-1",
        actor_id="ACTOR-1",
        correlation_id="CORR-1",
        evidence=[{"evidence_id": "E-1", "tenant_id": "TENANT-1"}],
        iocs=[{
            "ioc_id": "IOC-1",
            "ioc_type": "ip",
            "value": "1.2.3.4",
            "provenance": {"source": "provider-a"},
        }],
    )


def test_v1_projections_preserve_identity_and_ioc_metadata():
    context = _context()
    for projection in (
        context.agent_projection(),
        context.reasoning_projection(),
        context.copilot_projection(),
    ):
        assert projection["case_id"] == "CASE-1"
        assert projection["tenant_id"] == "TENANT-1"
        assert projection["correlation_id"] == "CORR-1"
        assert projection["iocs"][0] == {
            "ioc_id": "IOC-1",
            "ioc_type": "ip",
            "value": "1.2.3.4",
            "provenance": {"source": "provider-a"},
        }


def test_agent_projection_contains_no_authorization_capability_or_secrets():
    projection = _context().agent_projection()
    assert "authorization" not in projection
    assert "authorization_capability" not in projection
    assert "token" not in projection
    assert "credentials" not in projection


def test_reasoning_projection_is_consumer_safe():
    projection = _context().reasoning_projection()
    assert projection["evidence"][0]["evidence_id"] == "E-1"
    assert projection["intelligence_provenance"] == {}
    assert "actions" not in projection


def test_report_projection_is_result_oriented():
    projection = _context().report_projection({"case_id": "CASE-1", "confidence": 0.8})
    assert projection["result"]["confidence"] == 0.8
    assert projection["iocs"][0]["provenance"]["source"] == "provider-a"
