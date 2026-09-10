"""Google OpenID Connect boundary with explicit state and nonce validation."""
from dataclasses import dataclass
import os, secrets
from urllib.parse import urlencode
import requests
import jwt

GOOGLE_ISSUER = "https://accounts.google.com"
GOOGLE_DISCOVERY = GOOGLE_ISSUER + "/.well-known/openid-configuration"

@dataclass(frozen=True)
class GoogleClaims:
    subject: str
    email: str
    name: str

class GoogleOIDC:
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None):
        self.client_id = client_id or os.getenv("GOOGLE_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "")

    @property
    def configured(self): return bool(self.client_id and self.client_secret and self.redirect_uri)

    def begin(self):
        if not self.configured: raise RuntimeError("google_oidc_not_configured")
        discovery = requests.get(GOOGLE_DISCOVERY, timeout=5).json()
        state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        params = {"client_id": self.client_id, "response_type": "code", "scope": "openid email profile", "redirect_uri": self.redirect_uri, "state": state, "nonce": nonce, "access_type": "online", "prompt": "select_account"}
        return discovery["authorization_endpoint"] + "?" + urlencode(params), state, nonce

    def complete(self, code, state, expected_state, nonce, expected_nonce):
        if not code or not state or not secrets.compare_digest(state, expected_state or "") or not secrets.compare_digest(nonce, expected_nonce or ""): raise ValueError("oauth_state_invalid")
        discovery = requests.get(GOOGLE_DISCOVERY, timeout=5).json()
        token = requests.post(discovery["token_endpoint"], data={"code": code, "client_id": self.client_id, "client_secret": self.client_secret, "redirect_uri": self.redirect_uri, "grant_type": "authorization_code"}, timeout=5).json()
        signing_key = jwt.PyJWKClient(discovery["jwks_uri"]).get_signing_key_from_jwt(token["id_token"])
        claims = jwt.decode(token["id_token"], signing_key.key, algorithms=["RS256"], audience=self.client_id, issuer=GOOGLE_ISSUER, options={"require": ["exp", "iat", "iss", "sub", "aud", "nonce"]})
        if not secrets.compare_digest(str(claims.get("nonce", "")), str(expected_nonce or "")) or claims.get("email_verified") is not True or not claims.get("email"): raise ValueError("oauth_claims_invalid")
        return GoogleClaims(str(claims["sub"]), str(claims["email"]).lower(), str(claims.get("name") or claims["email"]))
