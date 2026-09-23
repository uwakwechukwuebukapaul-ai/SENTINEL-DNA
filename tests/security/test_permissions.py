from services.auth.permissions import PERMISSIONS, ROLE_ALIASES

def test_enterprise_roles_and_permissions():
    ordinary_roles = {"ADMIN", "SOC_MANAGER", "ANALYST", "VIEWER"}
    staging_role = "STAGING_BOOTSTRAP_REVIEWER"
    assert set(ROLE_ALIASES) == ordinary_roles | {staging_role}
    assert ROLE_ALIASES[staging_role] == "staging_bootstrap_reviewer"

    staging_capabilities = {
        permission
        for permission, roles in PERMISSIONS.items()
        if ROLE_ALIASES[staging_role] in roles
    }
    assert staging_capabilities == {
        "identity:staging_bootstrap_request",
        "identity:staging_bootstrap_approve",
    }

    assert PERMISSIONS["identity:staging_bootstrap_request"] == {
        "admin", "soc_manager", "analyst", "viewer", "staging_bootstrap_reviewer"
    }
    assert PERMISSIONS["identity:staging_bootstrap_approve"] == {
        "admin", "soc_manager", "staging_bootstrap_reviewer"
    }
    assert "admin" in PERMISSIONS["cases:assign"]
    assert "viewer" not in PERMISSIONS["cases:notes"]
