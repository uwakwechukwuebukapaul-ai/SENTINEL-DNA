"""Configuration and adapter contracts for enterprise identity providers.

The adapters validate provider metadata and claims, but never assign Sentinel
DNA roles or tenants.  Those remain canonical-authority responsibilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol
import requests
from urllib.parse import urlparse

from .authentication import AuthenticatedProviderPrincipal


class EnterpriseIdentityError(ValueError):
    """Raised when an enterprise identity cannot be trusted."""


class JwksOidcVerifier:
    """Fail-closed OIDC verifier with bounded discovery and PyJWT validation."""

    def __init__(self, transport=requests.get, timeout: int = 5):
        self.transport, self.timeout = transport, timeout

    def verify(self, id_token: str, configuration: "EnterpriseProviderConfiguration", nonce: str) -> "VerifiedEnterpriseClaims":
        try:
            import jwt
            response = self.transport(configuration.jwks_uri, timeout=self.timeout, allow_redirects=False, headers={"Accept": "application/json"})
            if response.status_code != 200 or len(response.content) > 262144:
                raise EnterpriseIdentityError("provider_jwks_unavailable")
            document = response.json()
            keys = document.get("keys") if isinstance(document, dict) else None
            if not isinstance(keys, list) or not keys or len(keys) > 32:
                raise EnterpriseIdentityError("provider_jwks_invalid")
            signing = [key for key in keys if isinstance(key, dict) and key.get("use", "sig") == "sig" and key.get("alg", "RS256") in {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}]
            if not signing: raise EnterpriseIdentityError("provider_signing_keys_invalid")
            key = jwt.PyJWKClient(configuration.jwks_uri).get_signing_key_from_jwt(id_token).key
            claims = jwt.decode(id_token, key, algorithms=[key.algorithm_name], audience=configuration.audience or configuration.client_id, issuer=configuration.issuer, options={"require": ["iss", "sub", "aud", "exp", "iat", "nonce"]})
        except EnterpriseIdentityError:
            raise
        except Exception as exc:
            raise EnterpriseIdentityError("provider_signature_invalid") from exc
        subject, email = claims.get("sub"), claims.get("email") or claims.get("preferred_username")
        if not isinstance(subject, str) or not subject.strip() or not isinstance(email, str) or "@" not in email:
            raise EnterpriseIdentityError("provider_claims_invalid")
        provider_tenant = str(claims.get(configuration.tenant_claim or "tid") or claims.get("hd") or "").strip()
        return VerifiedEnterpriseClaims(configuration.issuer, configuration.audience or configuration.client_id, subject, email.lower(), provider_tenant, str(claims.get("nonce")))


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
        if self.provider == "entra" and not self.tenant_claim:
            raise EnterpriseIdentityError("entra_tenant_claim_required")


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

    def verify(self, id_token: str, nonce: str) -> AuthenticatedProviderPrincipal:
        principal = super().verify(id_token, nonce)
        if not principal.tenant_id:
            raise EnterpriseIdentityError("entra_tenant_invalid")
        return principal


class OktaProviderAdapter(EnterpriseProviderAdapter):
    """Okta OIDC adapter; issuer and audience are exact-match validated."""

    def verify(self, id_token: str, nonce: str) -> AuthenticatedProviderPrincipal:
        principal = super().verify(id_token, nonce)
        if not principal.tenant_id or "." not in urlparse(self.configuration.issuer).hostname:
            raise EnterpriseIdentityError("okta_organization_invalid")
        return principal


class GoogleWorkspaceProviderAdapter(EnterpriseProviderAdapter):
    """Google Workspace adapter; domain/Workspace allow-listing is external policy."""

    def __init__(self, configuration, verifier, allowed_domains: frozenset[str] = frozenset()):
        super().__init__(configuration, verifier)
        self.allowed_domains = frozenset(domain.lower().strip() for domain in allowed_domains)

    def verify(self, id_token: str, nonce: str) -> AuthenticatedProviderPrincipal:
        principal = super().verify(id_token, nonce)
        domain = principal.claims[0][1].rsplit("@", 1)[-1].lower()
        if self.allowed_domains and domain not in self.allowed_domains:
            raise EnterpriseIdentityError("google_workspace_domain_untrusted")
        return principal


class ProviderTenantTrustService:
    """Resolve active provider trust without creating tenants or memberships."""

    def __init__(self, db: Any): self.db = db

    def require(self, provider: str, issuer: str, external_tenant_id: str, canonical_tenant_id: str) -> bool:
        if not all(isinstance(value, str) and value.strip() for value in (provider, issuer, external_tenant_id, canonical_tenant_id)):
            raise EnterpriseIdentityError("provider_trust_incomplete")
        with self.db.session() as connection:
            row = connection.execute("SELECT 1 FROM canonical_provider_tenant_trusts WHERE provider=? AND issuer=? AND external_tenant_id=? AND canonical_tenant_id=? AND status='active'", (provider, issuer, external_tenant_id, canonical_tenant_id)).fetchone()
        if not row: raise EnterpriseIdentityError("provider_tenant_trust_denied")
        return True


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
