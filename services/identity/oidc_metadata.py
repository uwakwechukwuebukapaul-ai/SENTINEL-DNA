"""Non-destructive OIDC discovery and JWKS validation boundary."""
from __future__ import annotations
import ipaddress, json
from dataclasses import dataclass
from urllib.parse import urlparse

class OidcMetadataError(ValueError): pass

@dataclass(frozen=True)
class OidcMetadataValidationResult:
    valid: bool
    reason: str
    signing_key_count: int = 0

class OidcMetadataValidator:
    def __init__(self, transport, max_response_bytes=262144, max_keys=32):
        if transport is None or not callable(transport): raise ValueError("oidc_metadata_transport_required")
        if max_response_bytes <= 0 or max_keys <= 0: raise ValueError("oidc_metadata_limits_invalid")
        self.transport, self.max_response_bytes, self.max_keys = transport, max_response_bytes, max_keys

    def validate(self, config, discovery_url=None):
        try:
            for url in (config.issuer, config.authorization_endpoint, config.token_endpoint, config.jwks_uri): self._url(url)
            discovery = self._fetch(discovery_url or config.issuer.rstrip("/") + "/.well-known/openid-configuration")
            if discovery.get("issuer") != config.issuer: raise OidcMetadataError("oidc_discovery_issuer_mismatch")
            for field, expected in (("authorization_endpoint", config.authorization_endpoint), ("token_endpoint", config.token_endpoint), ("jwks_uri", config.jwks_uri)):
                if discovery.get(field) != expected: raise OidcMetadataError("oidc_discovery_endpoint_mismatch")
            algorithms = discovery.get("id_token_signing_alg_values_supported", [])
            if not isinstance(algorithms, list) or not set(algorithms).intersection(config.signing_algorithms): raise OidcMetadataError("oidc_discovery_algorithm_mismatch")
            jwks = self._fetch(config.jwks_uri); keys = jwks.get("keys")
            if not isinstance(keys, list) or not keys or len(keys) > self.max_keys: raise OidcMetadataError("oidc_jwks_keys_invalid")
            kids = set()
            for key in keys: self._validate_key(key, config.signing_algorithms, kids)
            return OidcMetadataValidationResult(True, "metadata_validated", len(keys))
        except OidcMetadataError as exc: return OidcMetadataValidationResult(False, str(exc))
        except Exception: return OidcMetadataValidationResult(False, "oidc_metadata_unavailable")

    def _fetch(self, url):
        self._url(url); response = self.transport(url, timeout=5, allow_redirects=False, headers={"Accept":"application/json"})
        if not isinstance(response, tuple) or len(response) != 2: raise OidcMetadataError("oidc_metadata_response_invalid")
        status, body = response
        if status != 200 or not isinstance(body, (str, bytes)) or len(body) > self.max_response_bytes: raise OidcMetadataError("oidc_metadata_response_invalid")
        try: value = json.loads(body)
        except Exception as exc: raise OidcMetadataError("oidc_metadata_json_invalid") from exc
        if not isinstance(value, dict): raise OidcMetadataError("oidc_metadata_json_invalid")
        return value

    @staticmethod
    def _url(value):
        parsed = urlparse(str(value or ""))
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment: raise OidcMetadataError("oidc_endpoint_untrusted")
        try:
            address = ipaddress.ip_address(parsed.hostname)
            if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_unspecified: raise OidcMetadataError("oidc_endpoint_untrusted")
        except ValueError:
            if parsed.hostname.lower() in {"localhost", "metadata.google.internal", "169.254.169.254"}: raise OidcMetadataError("oidc_endpoint_untrusted")

    @staticmethod
    def _validate_key(key, allowed, kids):
        if not isinstance(key, dict) or key.get("kty") not in {"RSA", "EC"} or key.get("alg") not in allowed or key.get("use", "sig") != "sig": raise OidcMetadataError("oidc_jwk_invalid")
        kid = key.get("kid")
        if not isinstance(kid, str) or not kid or kid in kids: raise OidcMetadataError("oidc_jwk_kid_ambiguous")
        kids.add(kid)
        if key["kty"] == "RSA" and (not isinstance(key.get("n"), str) or not isinstance(key.get("e"), str)): raise OidcMetadataError("oidc_jwk_invalid")
        if key["kty"] == "EC" and (key.get("crv") not in {"P-256", "P-384", "P-521"} or not isinstance(key.get("x"), str) or not isinstance(key.get("y"), str)): raise OidcMetadataError("oidc_jwk_invalid")
