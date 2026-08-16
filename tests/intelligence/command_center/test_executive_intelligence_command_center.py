from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.command_center.executive_intelligence_command_center import ExecutiveIntelligenceCommandCenter
from services.intelligence.command_center.executive_intelligence_command_center_service import ExecutiveIntelligenceCommandCenterService
def test_command_center_is_deterministic_tenant_scoped_and_frozen():
    a=ExecutiveIntelligenceCommandCenterService(None,None,None,None).derive('a')['command_center']; b=ExecutiveIntelligenceCommandCenterService(None,None,None,None).derive('b')['command_center']; assert a['command_center_id']!=b['command_center_id']; assert a['advisory_only']
    with pytest.raises(FrozenInstanceError): ExecutiveIntelligenceCommandCenter('t','i').unified_executive_intelligence_posture='x'
