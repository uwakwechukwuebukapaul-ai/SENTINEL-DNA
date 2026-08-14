from services.governance import GovernanceService,GovernancePolicy
def test_policy_creation(): s=GovernanceService(); assert s.create_policy(GovernancePolicy("p","t","P","security","x")).policy_id=="p"
def test_policy_serialization(): assert "policy_id" in GovernancePolicy("p","t","P","security","x").to_dict()
def test_policy_evaluation(): assert GovernanceService().evaluate_ai_request("default",{}).allowed
def test_ai_restriction(): assert not GovernanceService().evaluate_ai_request("default",{"execute_actions":True}).allowed
def test_soar_blocking(): assert not GovernanceService().evaluate_soar_action("default",{"destructive":True}).allowed
def test_approval_required(): assert GovernanceService().evaluate_soar_action("default",{"external":True}).reason=="approval_required"
def test_investigation_access(): assert GovernanceService().evaluate_investigation_access("tenant",{}).allowed
def test_tenant_policy_isolation(): assert GovernanceService().evaluate_ai_request("other",{"execute_actions":True}).reason=="ai_actions_restricted"
def test_audit_logging(): s=GovernanceService(); s.create_policy(GovernancePolicy("p","t","P","security","x")); assert s.audit.events
def test_backward_compatibility(): assert GovernanceService().restricted("delete_evidence")
