"""Provider-neutral, fail-closed OIDC integration contract.

This module intentionally contains no network client or JWT implementation.
Production authentication remains deferred until an approved verifier,
configuration, and provider-tenant trust relationship exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .authentication import AuthenticatedProviderPrincipal, CanonicalAuthenticationError
from .bindings import IdentityBindingService


class PyJwtOidcVerifier:
    """Cryptographic verifier backed by PyJWT's JWKS implementation."""

    def __init__(self, jwks_url: str, allowed_algorithms: tuple[str, ...] = ("RS256",), leeway: int = 0, tenant_claim: str = "tid"):
        if not jwks_url.startswith("https://"): raise OidcTrustError("oidc_jwks_endpoint_untrusted")
        if not allowed_algorithms or any(algorithm not in {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"} for algorithm in allowed_algorithms): raise OidcTrustError("oidc_algorithm_untrusted")
        if leeway < 0 or leeway > 300: raise OidcTrustError("oidc_clock_skew_invalid")
        self.jwks_url, self.allowed_algorithms, self.leeway, self.tenant_claim = jwks_url, allowed_algorithms, leeway, tenant_claim

    def verify(self, authorization_code: str, config: OidcProviderConfiguration, state: str, nonce: str, code_verifier: str) -> VerifiedOidcClaims:
        try:
            import jwt
            from jwt import PyJWKClient
            key = PyJWKClient(self.jwks_url).get_signing_key_from_jwt(authorization_code).key
            claims = jwt.decode(authorization_code, key, algorithms=list(self.allowed_algorithms), audience=config.audience, issuer=config.issuer, leeway=self.leeway, options={"require": ["exp", "sub", self.tenant_claim], "verify_iat": True, "verify_nbf": True})
        except Exception as exc:
            raise OidcTrustError("oidc_cryptographic_verification_failed") from exc
        token_nonce = claims.get("nonce")
        if nonce and token_nonce != nonce: raise OidcTrustError("oidc_nonce_invalid")
        external_subject, provider_tenant_id = claims.get("sub"), claims.get(self.tenant_claim)
        if not isinstance(external_subject, str) or not external_subject.strip(): raise OidcTrustError("oidc_subject_missing")
        if not isinstance(provider_tenant_id, str) or not provider_tenant_id.strip(): raise OidcTrustError("oidc_provider_tenant_missing")
        return VerifiedOidcClaims(config.issuer, config.audience, external_subject, provider_tenant_id, "oidc", "oidc")


class OidcTrustError(ValueError): pass


@dataclass(frozen=True)
class OidcProviderConfiguration:
    provider: str
    issuer: str
    client_id: str
    audience: str
    redirect_uri: str
    trusted_tenant_id: str

    def validate(self):
        values = (self.provider, self.issuer, self.client_id, self.audience, self.redirect_uri, self.trusted_tenant_id)
        if not all(str(value).strip() for value in values): raise OidcTrustError("oidc_configuration_incomplete")
        if not self.issuer.startswith("https://"): raise OidcTrustError("oidc_issuer_untrusted")


@dataclass(frozen=True)
class VerifiedOidcClaims:
    issuer: str
    audience: str
    external_subject: str
    provider_tenant_id: str
    authentication_method: str = "oidc"
    credential_id: str = ""


class OidcVerifier(Protocol):
    def verify(self, authorization_code: str, config: OidcProviderConfiguration, state: str, nonce: str, code_verifier: str) -> VerifiedOidcClaims: ...


class OidcProviderAdapter:
    """Adapter boundary requiring an independently trusted OIDC verifier."""

    def __init__(self, config: OidcProviderConfiguration, verifier: OidcVerifier, bindings: IdentityBindingService):
        config.validate()
        if verifier is None or not callable(getattr(verifier, "verify", None)): raise ValueError("oidc_verifier_required")
        if bindings is None or not callable(getattr(bindings, "resolve", None)): raise ValueError("identity_binding_service_required")
        self.config, self.verifier, self.bindings = config, verifier, bindings

    def authenticate(self, authorization_code: str, state: str, nonce: str, code_verifier: str) -> AuthenticatedProviderPrincipal:
        if not all(str(value or "").strip() for value in (authorization_code, state, nonce, code_verifier)):
            raise OidcTrustError("oidc_request_incomplete")
        try: claims = self.verifier.verify(authorization_code, self.config, state, nonce, code_verifier)
        except Exception as exc: raise OidcTrustError("oidc_verification_failed") from exc
        if not isinstance(claims, VerifiedOidcClaims): raise OidcTrustError("oidc_claims_unverified")
        if claims.issuer != self.config.issuer or claims.audience != self.config.audience: raise OidcTrustError("oidc_claims_untrusted")
        if claims.provider_tenant_id != self.config.trusted_tenant_id: raise OidcTrustError("oidc_provider_tenant_untrusted")
        if not claims.external_subject.strip(): raise OidcTrustError("oidc_subject_missing")
        try: binding = self.bindings.resolve(self.config.provider, claims.external_subject)
        except Exception as exc: raise OidcTrustError("oidc_identity_binding_denied") from exc
        return AuthenticatedProviderPrincipal(self.config.provider, claims.external_subject, self.config.trusted_tenant_id, binding.actor_id, claims.authentication_method, claims.credential_id, external_subject=claims.external_subject)
