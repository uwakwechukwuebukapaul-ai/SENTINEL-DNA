"""Non-destructive, fail-closed OIDC deployment readiness validation."""
from __future__ import annotations
import importlib.util, ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse
from .oidc_config import OidcRuntimeConfiguration, OidcSecretProvider

@dataclass(frozen=True)
class OidcDeploymentReadiness:
    status: str
    reason: str
    checks: tuple[str, ...] = ()

class OidcDeploymentReadinessValidator:
    def __init__(self, secret_provider=None, trust_service=None, production=True):
        self.secret_provider = secret_provider or OidcSecretProvider(); self.trust_service = trust_service; self.production = production
    def validate(self, configuration: OidcRuntimeConfiguration | None = None, metadata_validator=None):
        config = configuration or OidcRuntimeConfiguration.from_environment()
        try: config.validate(self.production)
        except Exception as exc: return OidcDeploymentReadiness("CONFIGURATION_INVALID" if config.provider else "CONFIGURATION_INCOMPLETE", str(exc))
        if not self.secret_provider.get(config.client_secret_reference): return OidcDeploymentReadiness("CONFIGURATION_INCOMPLETE", "client_secret_unavailable")
        for endpoint in (config.issuer, config.authorization_endpoint, config.token_endpoint, config.jwks_uri, config.redirect_uri):
            if not self._safe_endpoint(endpoint): return OidcDeploymentReadiness("CONFIGURATION_INVALID", "oidc_endpoint_untrusted")
        if not importlib.util.find_spec("jwt"): return OidcDeploymentReadiness("CRYPTOGRAPHY_UNAVAILABLE", "oidc_verifier_unavailable")
        if not config.external_tenant_id or self.trust_service is None: return OidcDeploymentReadiness("TRUST_NOT_ESTABLISHED", "provider_tenant_trust_missing")
        try: self.trust_service.resolve(config.provider, config.issuer, config.external_tenant_id)
        except Exception: return OidcDeploymentReadiness("TRUST_NOT_ESTABLISHED", "provider_tenant_trust_missing")
        if metadata_validator is None: return OidcDeploymentReadiness("METADATA_UNAVAILABLE", "oidc_metadata_validator_unavailable")
        metadata = metadata_validator.validate(config)
        if not metadata.valid:
            reason = metadata.reason
            return OidcDeploymentReadiness("METADATA_UNAVAILABLE" if "unavailable" in reason or "response" in reason else "METADATA_INVALID", reason)
        return OidcDeploymentReadiness("READY", "configuration_ready", ("configuration", "secret", "verifier", "trust", "metadata"))
    def _safe_endpoint(self, value):
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname: return False
        try:
            address = ipaddress.ip_address(parsed.hostname)
            if address.is_private or address.is_loopback or address.is_link_local or address.is_unspecified or address.is_reserved: return False
        except ValueError:
            if parsed.hostname.lower() in {"localhost", "metadata.google.internal", "169.254.169.254"}: return False
        return True
