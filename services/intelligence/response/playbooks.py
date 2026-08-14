from .models import ResponseAction

PLAYBOOKS = {
    "phishing": ("collect_email_artifacts", "notify_analyst"),
    "credential_compromise": ("revoke_session_recommendation", "collect_authentication_context"),
    "malware": ("collect_endpoint_artifacts", "containment_recommendation"),
    "suspicious_network": ("collect_network_context", "block_recommendation"),
}
def actions_for(incident_type):
    return [ResponseAction(f"{incident_type}-{index}", action, f"Simulated recommendation: {action}") for index, action in enumerate(PLAYBOOKS.get(incident_type, ("collect_context",)), 1)]
