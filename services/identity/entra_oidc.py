"""Bounded Microsoft Entra OIDC foundation.

No identity is provisioned here.  A verified Entra tuple must resolve to an
existing local ``users.id`` through the additive binding table.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import re
import secrets
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests
import jwt

from database.connection import database
from .authentication import AuthenticatedProviderPrincipal


ENTRA_ROLES = frozenset({"sdna.requester", "sdna.reviewer"})
ENTRA_CONFIGURATION_ENV = {
    "tenant_id": "SENTINEL_DNA_ENTRA_TENANT_ID",
    "client_id": "SENTINEL_DNA_ENTRA_CLIENT_ID",
    "redirect_uri": "SENTINEL_DNA_ENTRA_REDIRECT_URI",
    "certified_origin": "SENTINEL_DNA_CERTIFIED_ORIGIN",
    "issuer": "SENTINEL_DNA_ENTRA_ISSUER",
    "authorization_endpoint": "SENTINEL_DNA_ENTRA_AUTHORIZATION_ENDPOINT",
    "token_endpoint": "SENTINEL_DNA_ENTRA_TOKEN_ENDPOINT",
    "jwks_uri": "SENTINEL_DNA_ENTRA_JWKS_URI",
    "discovery_uri": "SENTINEL_DNA_ENTRA_DISCOVERY_URI",
}
_GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)


class EntraOidcError(ValueError):
    pass


@dataclass(frozen=True)
class EntraIdentityTuple:
    issuer: str
    tenant_id: str
    object_id: str
    subject_id: str

    def validate(self) -> None:
        if not all(isinstance(x, str) and x.strip() for x in (self.issuer, self.tenant_id, self.object_id, self.subject_id)):
            raise EntraOidcError("entra_identity_tuple_invalid")


@dataclass(frozen=True)
class VerifiedEntraToken:
    identity: EntraIdentityTuple
    audience: str
    roles: frozenset[str]


@dataclass(frozen=True)
class EntraOidcConfig:
    client_secret_reference: str
    redirect_uri: str
    certified_origin: str
    issuer: str
    tenant_id: str
    client_id: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    discovery_uri: str
    algorithm: str = "RS256"
    clock_skew_seconds: int = 60

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> "EntraOidcConfig":
        values = os.environ if environ is None else environ
        required = {field: str(values.get(name, "")).strip() for field, name in ENTRA_CONFIGURATION_ENV.items()}
        required["client_secret_reference"] = str(values.get("SENTINEL_DNA_ENTRA_CLIENT_SECRET_REFERENCE", "")).strip()
        missing = [name for field, name in ENTRA_CONFIGURATION_ENV.items() if not required[field]]
        if not required["client_secret_reference"]:
            missing.append("SENTINEL_DNA_ENTRA_CLIENT_SECRET_REFERENCE")
        if missing:
            raise EntraOidcError("entra_configuration_missing")
        return cls(**required)

    def validate(self) -> None:
        if not _GUID.fullmatch(self.tenant_id) or not _GUID.fullmatch(self.client_id):
            raise EntraOidcError("entra_identifier_invalid")
        if self.algorithm != "RS256" or not self.client_secret_reference.strip():
            raise EntraOidcError("entra_configuration_invalid")
        for value in (self.issuer, self.authorization_endpoint, self.token_endpoint, self.jwks_uri, self.discovery_uri, self.redirect_uri, self.certified_origin):
            _safe_https(value)
        if _origin_key(self.redirect_uri) != _origin_key(self.certified_origin):
            raise EntraOidcError("entra_redirect_origin_invalid")
        if not 0 <= self.clock_skew_seconds <= 300:
            raise EntraOidcError("entra_clock_skew_invalid")


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _pkce_verifier() -> str:
    return _b64(secrets.token_bytes(32))


def pkce_challenge(verifier: str) -> str:
    return _b64(hashlib.sha256(verifier.encode("ascii")).digest())


def _safe_https(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise EntraOidcError("entra_endpoint_untrusted")
    try:
        address = ipaddress.ip_address(parsed.hostname)
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            raise EntraOidcError("entra_endpoint_untrusted")
    except ValueError:
        pass


def _origin_key(url: str) -> tuple[str, str, int | None]:
    parsed = urlparse(url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise EntraOidcError("entra_endpoint_untrusted") from exc
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), port or (443 if parsed.scheme.lower() == "https" else None)


class EntraDiscovery:
    def __init__(self, config: EntraOidcConfig, transport=requests.get):
        self.config = config
        self.transport = transport

    def validate(self) -> dict:
        self.config.validate()
        for url in (self.config.discovery_uri, self.config.issuer, self.config.authorization_endpoint, self.config.token_endpoint, self.config.jwks_uri, self.config.redirect_uri):
            _safe_https(url)
        response = self.transport(self.config.discovery_uri, timeout=5, allow_redirects=False, headers={"Accept": "application/json"})
        if response.status_code != 200 or len(response.content) > 262144:
            raise EntraOidcError("entra_discovery_unavailable")
        document = response.json()
        expected = {"issuer": self.config.issuer, "authorization_endpoint": self.config.authorization_endpoint, "token_endpoint": self.config.token_endpoint, "jwks_uri": self.config.jwks_uri}
        if any(document.get(key) != value for key, value in expected.items()):
            raise EntraOidcError("entra_discovery_mismatch")
        if self.config.algorithm not in document.get("id_token_signing_alg_values_supported", []):
            raise EntraOidcError("entra_algorithm_unadvertised")
        return document


def validate_jwks_document(document: object, algorithm: str = "RS256") -> tuple[dict, ...]:
    """Validate the untrusted JWKS envelope before PyJWT selects a key."""
    if not isinstance(document, Mapping) or not isinstance(document.get("keys"), list) or not document["keys"]:
        raise EntraOidcError("entra_jwks_invalid")
    seen: set[str] = set()
    validated: list[dict] = []
    for key in document["keys"]:
        if not isinstance(key, Mapping):
            raise EntraOidcError("entra_jwks_key_invalid")
        kid, kty = key.get("kid"), key.get("kty")
        if not isinstance(kid, str) or not kid or kid in seen:
            raise EntraOidcError("entra_jwks_kid_invalid")
        if kty != "RSA" or key.get("use", "sig") != "sig" or key.get("alg", algorithm) != algorithm:
            raise EntraOidcError("entra_jwks_key_incompatible")
        if not isinstance(key.get("n"), str) or not key.get("n") or not isinstance(key.get("e"), str) or not key.get("e"):
            raise EntraOidcError("entra_jwks_key_material_invalid")
        try:
            for material in (key["n"], key["e"]):
                base64.b64decode(material + "=" * (-len(material) % 4), altchars=b"-_", validate=True)
        except Exception as exc:
            raise EntraOidcError("entra_jwks_key_material_invalid") from exc
        seen.add(kid)
        validated.append(dict(key))
    return tuple(validated)


class EntraTokenClient:
    def __init__(self, config: EntraOidcConfig, client_secret_provider, transport=requests.post):
        self.config, self.client_secret_provider, self.transport = config, client_secret_provider, transport

    def exchange(self, code: str, verifier: str) -> dict:
        secret = self.client_secret_provider(self.config.client_secret_reference)
        if not secret:
            raise EntraOidcError("entra_client_secret_unavailable")
        response = self.transport(self.config.token_endpoint, data={"grant_type": "authorization_code", "client_id": self.config.client_id, "client_secret": secret, "code": code, "redirect_uri": self.config.redirect_uri, "code_verifier": verifier}, timeout=10, allow_redirects=False)
        if response.status_code != 200:
            raise EntraOidcError("entra_code_exchange_failed")
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("id_token"), str):
            raise EntraOidcError("entra_token_response_invalid")
        return payload


class EntraJwtValidator:
    def __init__(self, config: EntraOidcConfig, jwks_client_factory=jwt.PyJWKClient, jwks_transport=requests.get):
        self.config, self.jwks_client_factory, self.jwks_transport = config, jwks_client_factory, jwks_transport

    def validate(self, id_token: str, expected_nonce: str) -> VerifiedEntraToken:
        try:
            header = jwt.get_unverified_header(id_token)
            if header.get("alg") != self.config.algorithm or not header.get("kid"):
                raise EntraOidcError("entra_signing_key_invalid")
            response = self.jwks_transport(self.config.jwks_uri, timeout=5, allow_redirects=False, headers={"Accept": "application/json"})
            if response.status_code != 200 or len(response.content) > 262144:
                raise EntraOidcError("entra_jwks_unavailable")
            validate_jwks_document(response.json(), self.config.algorithm)
            key = self.jwks_client_factory(self.config.jwks_uri).get_signing_key_from_jwt(id_token).key
            claims = jwt.decode(id_token, key, algorithms=[self.config.algorithm], audience=self.config.client_id, issuer=self.config.issuer, leeway=self.config.clock_skew_seconds, options={"require": ["iss", "tid", "oid", "sub", "aud", "exp", "nbf", "iat", "nonce", "roles", "ver"], "verify_iat": True, "verify_nbf": True})
        except EntraOidcError:
            raise
        except Exception as exc:
            raise EntraOidcError("entra_token_invalid") from exc
        if not secrets.compare_digest(str(claims.get("nonce", "")), expected_nonce):
            raise EntraOidcError("entra_nonce_invalid")
        if claims.get("ver") != "2.0":
            raise EntraOidcError("entra_token_version_invalid")
        roles = claims.get("roles")
        if not isinstance(roles, list) or not roles or any(not isinstance(role, str) or not role for role in roles):
            raise EntraOidcError("entra_roles_invalid")
        roles = frozenset(roles)
        if not roles.intersection(ENTRA_ROLES):
            raise EntraOidcError("entra_role_required")
        identity = EntraIdentityTuple(str(claims["iss"]), str(claims["tid"]), str(claims["oid"]), str(claims["sub"]))
        identity.validate()
        if identity.issuer != self.config.issuer or identity.tenant_id != self.config.tenant_id or str(claims["aud"]) != self.config.client_id:
            raise EntraOidcError("entra_identity_claim_mismatch")
        return VerifiedEntraToken(identity, self.config.client_id, roles)


class EntraBindingRepository:
    def __init__(self, db=database):
        self.db = db

    def resolve(self, identity: EntraIdentityTuple):
        identity.validate()
        with self.db.session() as connection:
            rows = connection.execute("SELECT binding_id,user_id,status FROM entra_identity_bindings WHERE issuer=? AND tenant_id=? AND object_id=? AND subject_id=?", (identity.issuer, identity.tenant_id, identity.object_id, identity.subject_id)).fetchall()
        active = [row for row in rows if row["status"] == "active"]
        if len(active) != 1:
            raise EntraOidcError("entra_identity_binding_denied")
        return active[0]


def begin_transaction(session: dict, config: EntraOidcConfig) -> str:
    config.validate()
    state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), _pkce_verifier()
    now = int(time.time())
    session["entra_oidc_transaction"] = {"transaction_id": secrets.token_urlsafe(24), "state": state, "nonce": nonce, "verifier": verifier, "created_at": now, "expires_at": now + 300, "status": "pending", "consumed_at": None}
    params = {"client_id": config.client_id, "response_type": "code", "redirect_uri": config.redirect_uri, "response_mode": "query", "scope": "openid", "state": state, "nonce": nonce, "code_challenge": pkce_challenge(verifier), "code_challenge_method": "S256"}
    return config.authorization_endpoint + "?" + urlencode(params)


def consume_transaction(session: dict, returned_state: str) -> dict:
    transaction = session.pop("entra_oidc_transaction", None)
    if not isinstance(transaction, dict) or transaction.get("status") != "pending" or int(time.time()) >= int(transaction.get("expires_at", 0)):
        raise EntraOidcError("entra_transaction_expired")
    if not returned_state or not secrets.compare_digest(returned_state, str(transaction.get("state", ""))):
        raise EntraOidcError("entra_state_invalid")
    transaction["status"] = "consumed"
    transaction["consumed_at"] = int(time.time())
    return transaction


class ExternalSecretReferenceResolver:
    """Resolve a named secret reference supplied by the deployment runtime."""

    def __init__(self, environ: Mapping[str, str] | None = None):
        self.environ = os.environ if environ is None else environ

    def __call__(self, reference: str) -> str:
        reference = str(reference or "").strip()
        if not reference:
            return ""
        # References identify secret-file settings; secret contents are never
        # accepted as application configuration values.
        file_keys = [reference + "_FILE"]
        # Sentinel DNA's deployment convention allows a short, lowercase
        # reference (for example ``entra_client_secret``) to identify the
        # canonical ``SENTINEL_DNA_ENTRA_CLIENT_SECRET_FILE`` setting.
        canonical_key = "SENTINEL_DNA_" + reference.upper() + "_FILE"
        if canonical_key not in file_keys:
            file_keys.append(canonical_key)
        path = next((self.environ.get(key, "") for key in file_keys if self.environ.get(key, "")), "")
        if not path and reference.endswith("_FILE"):
            path = self.environ.get(reference, "")
        if not path:
            return ""
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            return ""


class EntraEnterpriseFlow:
    """Provider-neutral registry flow backed by the hardened Entra primitives."""

    provider = "entra"
    display_name = "Microsoft Entra ID"

    def __init__(self, config: EntraOidcConfig, secret_resolver=None, discovery=None,
                 token_client=None, jwt_validator=None, binding_repository=None):
        config.validate()
        self.configuration = config
        self.secret_resolver = secret_resolver or ExternalSecretReferenceResolver()
        self.discovery = discovery or EntraDiscovery(config)
        self.token_client = token_client or EntraTokenClient(config, self.secret_resolver)
        self.jwt_validator = jwt_validator or EntraJwtValidator(config)
        self.binding_repository = binding_repository or EntraBindingRepository()

    def health_check(self) -> bool:
        """Return readiness without exposing error details or secret material."""
        try:
            if not self.secret_resolver(self.configuration.client_secret_reference):
                return False
            self.discovery.validate()
            return True
        except Exception:
            return False

    def begin(self):
        transaction = {}
        location = begin_transaction(transaction, self.configuration)
        record = transaction["entra_oidc_transaction"]
        return location, record["state"], record["nonce"]

    def complete(self, params, transaction):
        if not isinstance(transaction, dict):
            raise EntraOidcError("entra_transaction_invalid")
        if transaction.get("status") != "pending" or int(time.time()) >= int(transaction.get("expires_at", 0)):
            raise EntraOidcError("entra_transaction_expired")
        if params.get("error"):
            raise EntraOidcError("entra_provider_authentication_failed")
        returned_state = str(params.get("state") or "")
        expected_state = str(transaction.get("state") or "")
        if not returned_state or not expected_state or not secrets.compare_digest(returned_state, expected_state):
            raise EntraOidcError("entra_state_invalid")
        code = str(params.get("code") or "").strip()
        if not code:
            raise EntraOidcError("entra_code_missing")
        token = self.token_client.exchange(code, str(transaction.get("verifier") or ""))
        verified = self.jwt_validator.validate(token["id_token"], str(transaction.get("nonce") or ""))
        verified.identity.validate()
        return AuthenticatedProviderPrincipal(
            provider="entra",
            subject=verified.identity.subject_id,
            tenant_id=verified.identity.tenant_id,
            actor_id="",
            authentication_method="entra_oidc",
            credential_id=verified.identity.object_id,
            external_subject=verified.identity.object_id,
            claims=(
                ("issuer", verified.identity.issuer),
                ("tenant_id", verified.identity.tenant_id),
                ("object_id", verified.identity.object_id),
                ("subject_id", verified.identity.subject_id),
            ),
        )

    def resolve_bound_user(self, auth, principal):
        claims = dict(principal.claims)
        identity = EntraIdentityTuple(
            claims.get("issuer", ""), claims.get("tenant_id", ""),
            claims.get("object_id", ""), claims.get("subject_id", ""),
        )
        binding = self.binding_repository.resolve(identity)
        return auth.get_by_id(binding["user_id"])
