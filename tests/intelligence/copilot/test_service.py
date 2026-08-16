from services.intelligence.copilot.copilot_service import GovernedCopilotService
def test_context_reasoning_confidence_and_recommendations_are_advisory():
    service=GovernedCopilotService();context=service.context('a','case');result=service.reason('a','case');assert context['tenant_id']=='a';assert result['advisory_only'];assert result['confidence']['level']=='insufficient_data';assert result['recommendations']['advisory_only']
