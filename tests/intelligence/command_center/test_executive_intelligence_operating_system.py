from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.command_center.executive_intelligence_operating_system import ExecutiveIntelligenceOperatingSystem
from services.intelligence.command_center.executive_intelligence_operating_system_service import ExecutiveIntelligenceOperatingSystemService
def test_operating_system_is_tenant_scoped_frozen_and_advisory():
    a=ExecutiveIntelligenceOperatingSystemService(None,None).derive('a')['operating_system']; b=ExecutiveIntelligenceOperatingSystemService(None,None).derive('b')['operating_system']; assert a['operating_system_id']!=b['operating_system_id']; assert a['advisory_only']
    with pytest.raises(FrozenInstanceError): ExecutiveIntelligenceOperatingSystem('t','i').unified_operating_posture='x'
