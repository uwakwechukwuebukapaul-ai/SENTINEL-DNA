"""Strict environment-backed OIDC readiness configuration."""
from __future__ import annotations
import os
from dataclasses import dataclass
from urllib.parse import urlparse

class OidcConfigurationError(ValueError): pass

@dataclass(frozen=True)
class OidcReadiness:
    status: str
    reason: str

@dataclass(frozen=True)
class OidcRuntimeConfiguration:
    provider: str; issuer: str; authorization_endpoint: str; token_endpoint: str; jwks_uri: str; client_id: str; audience: str; redirect_uri: str; client_secret_reference: str; provider_tenant_claim: str; signing_algorithms: tuple[str, ...]; external_tenant_id: str = ""
    @classmethod
    def from_environment(cls, environ=None):
        env = environ or os.environ
        algorithms = tuple(x.strip() for x in env.get("OIDC_SIGNING_ALGORITHMS", "").split(",") if x.strip())
        return cls(*(env.get(key, "").strip() for key in ("OIDC_PROVIDER", "OIDC_ISSUER", "OIDC_AUTHORIZATION_ENDPOINT", "OIDC_TOKEN_ENDPOINT", "OIDC_JWKS_URI", "OIDC_CLIENT_ID", "OIDC_AUDIENCE", "OIDC_REDIRECT_URI", "OIDC_CLIENT_SECRET_REFERENCE", "OIDC_PROVIDER_TENANT_CLAIM")), algorithms, env.get("OIDC_EXTERNAL_TENANT_ID", "").strip())
    def validate(self, production=True):
        values = (self.provider, self.issuer, self.authorization_endpoint, self.token_endpoint, self.jwks_uri, self.client_id, self.audience, self.redirect_uri, self.provider_tenant_claim)
        if not all(values) or not self.signing_algorithms: raise OidcConfigurationError("oidc_configuration_incomplete")
        if not self.client_secret_reference: raise OidcConfigurationError("oidc_secret_reference_missing")
        if any(a not in {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"} for a in self.signing_algorithms): raise OidcConfigurationError("oidc_algorithm_untrusted")
        endpoints = (self.issuer, self.authorization_endpoint, self.token_endpoint, self.jwks_uri, self.redirect_uri)
        if production and any(urlparse(x).scheme != "https" or urlparse(x).hostname in {"localhost", "127.0.0.1"} for x in endpoints): raise OidcConfigurationError("oidc_https_required")
        if "*" in self.redirect_uri: raise OidcConfigurationError("oidc_redirect_uri_invalid")
        return True
    def readiness(self, secret_provider, production=True):
        try:
            self.validate(production)
            if not secret_provider.get(self.client_secret_reference): return {"ready": False, "reason": "oidc_client_secret_unavailable"}
            return {"ready": True, "reason": "ready"}
        except OidcConfigurationError as exc: return {"ready": False, "reason": str(exc)}
    def deployment_readiness(self, secret_provider, trust_service=None, production=True):
        try: self.validate(production)
        except OidcConfigurationError as exc: return OidcReadiness("CONFIGURATION_INVALID", str(exc))
        if not secret_provider.get(self.client_secret_reference): return OidcReadiness("CONFIGURATION_INCOMPLETE", "client_secret_unavailable")
        if not self.external_tenant_id or trust_service is None: return OidcReadiness("TRUST_NOT_ESTABLISHED", "provider_tenant_trust_missing")
        try: trust_service.resolve(self.provider, self.issuer, self.external_tenant_id)
        except Exception: return OidcReadiness("TRUST_NOT_ESTABLISHED", "provider_tenant_trust_missing")
        return OidcReadiness("READY", "configuration_ready")
    def is_ready(self, secret_provider, production=True):
        return self.readiness(secret_provider, production)["ready"]

class OidcSecretProvider:
    def __init__(self, environ=None): self.environ = environ or os.environ
    def get(self, reference): return self.environ.get(reference, "") if reference else ""
