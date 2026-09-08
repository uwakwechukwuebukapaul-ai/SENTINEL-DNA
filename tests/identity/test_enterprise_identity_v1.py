from services.identity.enterprise_providers import (
    EnterpriseIdentityError,
    EnterpriseProviderAdapter,
    EnterpriseProviderConfiguration,
    VerifiedEnterpriseClaims,
)
from services.identity.saml_foundation import SamlConfigurationError, SamlProviderConfiguration
from services.auth.webauthn import WebAuthnConfiguration, WebAuthnError


def config(provider="okta"):
    return EnterpriseProviderConfiguration(provider, "https://issuer.example", "client", "https://issuer.example/auth", "https://issuer.example/token", "https://issuer.example/keys", "https://app.example/auth/callback", "SECRET_REF")


class Verifier:
    def verify(self, token, configuration, nonce):
        return VerifiedEnterpriseClaims(configuration.issuer, configuration.client_id, "subject-1", "analyst@example.com", "workspace-1", nonce)


def test_enterprise_provider_adapter_requires_exact_verified_claims():
    principal = EnterpriseProviderAdapter(config(), Verifier()).verify("signed-token", "nonce")
    assert principal.provider == "okta"
    assert principal.authentication_method == "okta_oidc"
    assert dict(principal.claims)["email"] == "analyst@example.com"


def test_provider_configuration_rejects_non_https_endpoints():
    try:
        EnterpriseProviderConfiguration(**{**config().__dict__, "token_endpoint": "http://issuer.example/token"}).validate()
    except EnterpriseIdentityError as exc:
        assert str(exc) == "provider_endpoint_untrusted"
    else:
        raise AssertionError("untrusted endpoint accepted")


def test_saml_foundation_rejects_untrusted_acs():
    try:
        SamlProviderConfiguration("entity", "https://idp.example/sso", "CERT_REF", "http://app.example/acs").validate()
    except SamlConfigurationError as exc:
        assert str(exc) == "saml_endpoint_untrusted"
    else:
        raise AssertionError("untrusted ACS accepted")


def test_webauthn_configuration_requires_matching_production_origin():
    config = WebAuthnConfiguration("soc.example.com", "https://login.example.com", "Sentinel DNA", lambda *_: None)
    try:
        config.validate()
    except WebAuthnError as exc:
        assert str(exc) == "webauthn_rp_origin_mismatch"
    else:
        raise AssertionError("mismatched RP origin accepted")


def test_webauthn_configuration_rejects_missing_verifier():
    try:
        WebAuthnConfiguration("example.com", "https://example.com", "Sentinel DNA").validate()
    except WebAuthnError as exc:
        assert str(exc) == "webauthn_verifier_required"
    else:
        raise AssertionError("missing verifier accepted")
