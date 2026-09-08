"""Configuration and adapter contracts for enterprise identity providers.

The adapters validate provider metadata and claims, but never assign Sentinel
DNA roles or tenants.  Those remain canonical-authority responsibilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol
from urllib.parse import urlparse

from .authentication import AuthenticatedProviderPrincipal


class EnterpriseIdentityError(ValueError):
    """Raised when an enterprise identity cannot be trusted."""


@dataclass(frozen=True)
class EnterpriseProviderConfiguration:
    provider: str
    issuer: str
    client_id: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    redirect_uri: str
    client_secret_reference: str
    audience: str | None = None
    tenant_claim: str | None = None

    def validate(self) -> None:
        if self.provider not in {"entra", "okta", "google"}:
            raise EnterpriseIdentityError("provider_not_supported")
        values = (self.issuer, self.authorization_endpoint, self.token_endpoint, self.jwks_uri, self.redirect_uri, self.client_id, self.client_secret_reference)
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise EnterpriseIdentityError("provider_configuration_incomplete")
        for value in (self.issuer, self.authorization_endpoint, self.token_endpoint, self.jwks_uri, self.redirect_uri):
            parsed = urlparse(value)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise EnterpriseIdentityError("provider_endpoint_untrusted")
        if self.audience and self.audience != self.client_id:
            raise EnterpriseIdentityError("provider_audience_invalid")


@dataclass(frozen=True)
class VerifiedEnterpriseClaims:
    issuer: str
    audience: str
    subject: str
    email: str
    provider_tenant: str = ""
    nonce: str = ""


class EnterpriseTokenVerifier(Protocol):
    def verify(self, id_token: str, configuration: EnterpriseProviderConfiguration, nonce: str) -> VerifiedEnterpriseClaims: ...


class EnterpriseProviderAdapter:
    """Provider-specific trust boundary with injected cryptographic verifier."""

    def __init__(self, configuration: EnterpriseProviderConfiguration, verifier: EnterpriseTokenVerifier):
        configuration.validate()
        if verifier is None or not callable(getattr(verifier, "verify", None)):
            raise EnterpriseIdentityError("provider_verifier_required")
        self.configuration, self.verifier = configuration, verifier

    def verify(self, id_token: str, nonce: str) -> AuthenticatedProviderPrincipal:
        if not id_token.strip() or not nonce.strip():
            raise EnterpriseIdentityError("provider_authentication_incomplete")
        claims = self.verifier.verify(id_token, self.configuration, nonce)
        if not isinstance(claims, VerifiedEnterpriseClaims):
            raise EnterpriseIdentityError("provider_claims_unverified")
        if claims.issuer != self.configuration.issuer or claims.audience != self.configuration.client_id:
            raise EnterpriseIdentityError("provider_claims_untrusted")
        if claims.nonce != nonce or not claims.subject.strip() or "@" not in claims.email:
            raise EnterpriseIdentityError("provider_claims_invalid")
        return AuthenticatedProviderPrincipal(
            provider=self.configuration.provider,
            subject=claims.subject,
            tenant_id=claims.provider_tenant,
            actor_id="",
            authentication_method=f"{self.configuration.provider}_oidc",
            credential_id=claims.subject,
            external_subject=claims.subject,
            claims=(("email", claims.email),),
        )


class EntraProviderAdapter(EnterpriseProviderAdapter):
    """Microsoft Entra ID adapter; tenant claim is mandatory at verifier level."""


class OktaProviderAdapter(EnterpriseProviderAdapter):
    """Okta OIDC adapter; issuer and audience are exact-match validated."""


class GoogleWorkspaceProviderAdapter(EnterpriseProviderAdapter):
    """Google Workspace adapter; domain/Workspace allow-listing is external policy."""


def provider_configuration(provider: str, values: Mapping[str, str]) -> EnterpriseProviderConfiguration:
    prefix = {"entra": "ENTRA", "okta": "OKTA", "google": "GOOGLE"}.get(provider)
    if not prefix:
        raise EnterpriseIdentityError("provider_not_supported")
    config = EnterpriseProviderConfiguration(
        provider=provider,
        issuer=str(values.get(f"SENTINEL_DNA_{prefix}_OIDC_ISSUER", "")).strip(),
        client_id=str(values.get(f"SENTINEL_DNA_{prefix}_OIDC_CLIENT_ID", "")).strip(),
        authorization_endpoint=str(values.get(f"SENTINEL_DNA_{prefix}_OIDC_AUTHORIZATION_ENDPOINT", "")).strip(),
        token_endpoint=str(values.get(f"SENTINEL_DNA_{prefix}_OIDC_TOKEN_ENDPOINT", "")).strip(),
        jwks_uri=str(values.get(f"SENTINEL_DNA_{prefix}_OIDC_JWKS_URI", "")).strip(),
        redirect_uri=str(values.get(f"SENTINEL_DNA_{prefix}_OIDC_REDIRECT_URI", "")).strip(),
        client_secret_reference=str(values.get(f"SENTINEL_DNA_{prefix}_OIDC_CLIENT_SECRET_REFERENCE", "")).strip(),
        audience=str(values.get(f"SENTINEL_DNA_{prefix}_OIDC_AUDIENCE", "")).strip() or None,
        tenant_claim=str(values.get(f"SENTINEL_DNA_{prefix}_OIDC_TENANT_CLAIM", "")).strip() or None,
    )
    config.validate()
    return config
