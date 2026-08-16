import os
from services.identity.oidc_routes import OidcRouteConfiguration, create_oidc_blueprint

def test_oidc_routes_are_disabled_without_complete_configuration(monkeypatch):
    for key in OidcRouteConfiguration.REQUIRED: monkeypatch.delenv(key, raising=False)
    assert OidcRouteConfiguration.from_environment() is None
    assert create_oidc_blueprint(None) is None

def test_oidc_configuration_requires_all_values(monkeypatch):
    for key in OidcRouteConfiguration.REQUIRED: monkeypatch.setenv(key, "configured")
    assert OidcRouteConfiguration.from_environment()["OIDC_CLIENT_ID"] == "configured"
