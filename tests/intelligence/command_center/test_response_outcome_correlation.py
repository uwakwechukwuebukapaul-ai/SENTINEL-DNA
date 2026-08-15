from services.intelligence.command_center.response_outcome_correlation_service import ResponseOutcomeCorrelationService
def test_correlation_preserves_noncausal_boundary(): assert 'causal' in ResponseOutcomeCorrelationService().derive('a')['correlation']['temporal_association']
