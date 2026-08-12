"""Provider-neutral enterprise identity contracts for future SAML/OIDC and SCIM adapters."""
from __future__ import annotations
from dataclasses import dataclass
import base64
import hashlib
import hmac
import struct
import time
from urllib.parse import urlencode
from typing import Protocol

@dataclass(frozen=True)
class ExternalIdentity:
    subject: str
    email: str
    display_name: str
    provider: str

class SsoIdentityProvider(Protocol):
    def authorization_url(self, state: str, redirect_uri: str) -> str: ...
    def exchange_callback(self, code: str, redirect_uri: str) -> ExternalIdentity: ...

class MfaProvider(Protocol):
    def begin_challenge(self, user_id: str) -> str: ...
    def verify_challenge(self, user_id: str, challenge_id: str, response: str) -> bool: ...

class ScimProvisioner(Protocol):
    def upsert_user(self, identity: ExternalIdentity) -> str: ...
    def deactivate_user(self, external_subject: str) -> None: ...

class OidcProvider:
    """OIDC authorization-request adapter; token signature verification stays with a configured verifier."""
    def __init__(self, issuer: str, client_id: str, authorize_endpoint: str, token_verifier) -> None:
        if not issuer.startswith("https://") or not client_id or not authorize_endpoint.startswith("https://"): raise ValueError("OIDC configuration must use HTTPS")
        self.issuer, self.client_id, self.authorize_endpoint, self.token_verifier = issuer, client_id, authorize_endpoint, token_verifier
    def authorization_url(self, state: str, redirect_uri: str) -> str:
        if not state or not redirect_uri.startswith("https://"): raise ValueError("state and HTTPS redirect URI are required")
        return self.authorize_endpoint + "?" + urlencode({"client_id":self.client_id,"response_type":"code","scope":"openid email profile","state":state,"redirect_uri":redirect_uri})
    def exchange_callback(self, code: str, redirect_uri: str) -> ExternalIdentity:
        claims=self.token_verifier(code, redirect_uri)
        if claims.get("iss") != self.issuer or not claims.get("sub") or not claims.get("email"): raise PermissionError("OIDC token claims rejected")
        return ExternalIdentity(claims["sub"],claims["email"],claims.get("name",claims["email"]),"oidc")

class SamlProvider:
    """SAML adapter delegates XML signature validation to a deployment-approved verifier."""
    def __init__(self, entity_id: str, assertion_verifier) -> None: self.entity_id,self.assertion_verifier=entity_id,assertion_verifier
    def authorization_url(self, state: str, redirect_uri: str) -> str: raise NotImplementedError("SAML redirect binding is deployment-provider specific")
    def exchange_callback(self, code: str, redirect_uri: str) -> ExternalIdentity:
        claims=self.assertion_verifier(code, redirect_uri)
        if not claims.get("subject") or not claims.get("email"): raise PermissionError("SAML assertion rejected")
        return ExternalIdentity(claims["subject"],claims["email"],claims.get("display_name",claims["email"]),"saml")

class TotpMfaProvider:
    """RFC 6238-compatible verifier; secret storage is delegated to the secret manager."""
    def __init__(self, secret_lookup, step_seconds: int = 30) -> None: self.secret_lookup,self.step_seconds=secret_lookup,step_seconds
    def begin_challenge(self, user_id: str) -> str: return str(int(time.time()) // self.step_seconds)
    def verify_challenge(self, user_id: str, challenge_id: str, response: str) -> bool:
        if not response.isdigit() or len(response) != 6: return False
        secret=base64.b32decode(self.secret_lookup(user_id), casefold=True); counter=int(challenge_id)
        digest=hmac.new(secret,struct.pack(">Q",counter),hashlib.sha1).digest(); offset=digest[-1]&15
        expected=str((struct.unpack(">I",digest[offset:offset+4])[0]&0x7fffffff)%1_000_000).zfill(6)
        return hmac.compare_digest(expected,response)
