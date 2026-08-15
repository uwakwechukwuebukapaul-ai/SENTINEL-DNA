from services.intelligence.command_center.forecast_governance_service import ForecastGovernanceService

class StubAccuracy:
    def __init__(self, value): self.value=value
    def derive(self, tenant_id):
        result=dict(self.value); result['tenant_id']=tenant_id; return result

def test_empty_governance_is_explicit_and_advisory():
    result=ForecastGovernanceService(StubAccuracy({})).derive('tenant-a')
    assert result['governance_status']=='insufficient_evidence'
    assert result['early_warning_level']=='insufficient_evidence'
    assert result['advisory_only'] is True
    assert 'insufficient_history' in result['uncertainty']

def test_divergence_creates_deterministic_tenant_scoped_signal():
    value={'forecast_evaluations':[{'alignment':'diverged','forecast_signal_id':'f1'},{'alignment':'diverged','forecast_signal_id':'f2'}], 'confidence':'medium', 'evidence_strength':'moderate'}
    first=ForecastGovernanceService(StubAccuracy(value)).derive('tenant-a')
    second=ForecastGovernanceService(StubAccuracy(value)).derive('tenant-a')
    assert first==second
    assert first['governance_status']=='high_risk'
    assert first['governance_signals'][0]['severity']=='high'
    assert first['governance_signals'][0]['tenant_id']=='tenant-a'
    assert ForecastGovernanceService(StubAccuracy(value)).detail('tenant-b', first['governance_signals'][0]['stable_id']) is None
