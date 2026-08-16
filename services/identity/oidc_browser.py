"""Secure, provider-neutral OIDC authorization-code flow boundary."""
from __future__ import annotations
import base64, hashlib, secrets, time
from dataclasses import dataclass
from urllib.parse import urlencode
from .authentication import CanonicalAuthenticationError

class OidcBrowserError(ValueError): pass

@dataclass(frozen=True)
class OidcBrowserConfiguration:
    authorization_endpoint: str
    redirect_uri: str
    client_id: str
    scope: tuple[str, ...] = ("openid",)
    transaction_ttl: int = 300
    def validate(self):
        if not self.authorization_endpoint.startswith("https://") or not self.redirect_uri.startswith("https://"):
            raise OidcBrowserError("oidc_https_required")
        if not self.client_id.strip() or self.transaction_ttl <= 0 or self.transaction_ttl > 900: raise OidcBrowserError("oidc_configuration_invalid")

def _verifier(): return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
def _challenge(verifier): return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()

class OidcAuthorizationCodeFlow:
    """Owns browser transaction state; provider exchange remains injected."""
    def __init__(self, config: OidcBrowserConfiguration, provider_adapter, token_client):
        config.validate()
        if provider_adapter is None or token_client is None or not callable(getattr(token_client, "exchange", None)): raise ValueError("oidc_flow_dependencies_required")
        self.config, self.provider_adapter, self.token_client = config, provider_adapter, token_client

    def begin(self, session):
        state, nonce, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32), _verifier()
        session["oidc_transaction"] = {"state": state, "nonce": nonce, "verifier": verifier, "created_at": int(time.time())}
        query = {"response_type": "code", "client_id": self.config.client_id, "redirect_uri": self.config.redirect_uri, "scope": " ".join(self.config.scope), "state": state, "nonce": nonce, "code_challenge": _challenge(verifier), "code_challenge_method": "S256"}
        return self.config.authorization_endpoint + "?" + urlencode(query)

    def complete(self, session, params):
        transaction = session.pop("oidc_transaction", None)
        if not transaction or int(time.time()) - transaction["created_at"] > self.config.transaction_ttl: raise OidcBrowserError("oidc_transaction_expired")
        if params.get("state") != transaction["state"]: raise OidcBrowserError("oidc_state_invalid")
        if params.get("error"): raise OidcBrowserError("oidc_provider_authentication_failed")
        code = str(params.get("code") or "").strip()
        if not code: raise OidcBrowserError("oidc_code_missing")
        try: token = self.token_client.exchange(code, self.config.redirect_uri, transaction["verifier"])
        except Exception as exc: raise OidcBrowserError("oidc_code_exchange_failed") from exc
        if not isinstance(token, dict) or not token.get("id_token") or token.get("token_type", "Bearer").lower() != "bearer": raise OidcBrowserError("oidc_token_response_invalid")
        try: principal = self.provider_adapter.authenticate(token["id_token"], transaction["state"], transaction["nonce"], transaction["verifier"])
        except Exception as exc: raise OidcBrowserError("oidc_authentication_failed") from exc
        session.clear()
        session["canonical_principal"] = {"provider": principal.provider, "external_subject": principal.external_subject, "tenant_id": principal.tenant_id, "actor_id": principal.actor_id}
        return principal

    @staticmethod
    def logout(session): session.clear()

