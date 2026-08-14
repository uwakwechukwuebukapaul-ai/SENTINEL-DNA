from services.auth.permissions import PERMISSIONS, ROLE_ALIASES

def test_enterprise_roles_and_permissions():
    assert set(ROLE_ALIASES) == {"ADMIN", "SOC_MANAGER", "ANALYST", "VIEWER"}
    assert "admin" in PERMISSIONS["cases:assign"]
    assert "viewer" not in PERMISSIONS["cases:notes"]
