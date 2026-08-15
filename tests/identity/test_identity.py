from services.identity import *

def test_tenant_and_user_are_serializable_and_isolated():
    repo = IdentityRepository(); tenants = TenantService(repo)
    tenants.create_tenant("t1", "One"); tenants.create_tenant("t2", "Two")
    identity = IdentityService(repo); identity.create_user(user_id="u1", tenant_id="t1", username="one", email="one@example.test")
    assert repo.get_user("u1", "t2") is None and tenants.get_tenant("t1").to_dict()["name"] == "One"

def test_rbac_policy_and_sessions():
    identity = IdentityService(); identity.repository.save_role(Role("analyst", "Analyst", permissions=["investigations:read"]))
    identity.create_user(user_id="u", tenant_id="t", username="u", email="u@example.test"); identity.assign_role("u", "t", "analyst")
    assert identity.policy.can("u", "t", "investigations", "read")
    session = identity.sessions.create("u", "t"); assert identity.sessions.get(session.session_id, "t")
    assert identity.sessions.get(session.session_id, "other") is None

def test_unknown_or_inactive_users_are_denied():
    identity = IdentityService(); assert not identity.policy.can("missing", "t", "cases", "read")
