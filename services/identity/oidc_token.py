"""Injected, fixed-endpoint OIDC authorization-code exchange boundary."""
from __future__ import annotations
import requests

class OidcTokenExchangeError(ValueError): pass

class OidcTokenExchangeClient:
    def __init__(self, token_endpoint, client_id, client_secret, timeout=10):
        if not token_endpoint.startswith("https://"): raise ValueError("oidc_token_endpoint_untrusted")
        if not client_id or not client_secret or timeout <= 0 or timeout > 30: raise ValueError("oidc_token_client_invalid")
        self.token_endpoint, self.client_id, self.client_secret, self.timeout = token_endpoint, client_id, client_secret, timeout
    def exchange(self, code, redirect_uri, code_verifier):
        if not code or not redirect_uri.startswith("https://") or not code_verifier: raise OidcTokenExchangeError("oidc_exchange_request_invalid")
        try:
            response = requests.post(self.token_endpoint, data={"grant_type":"authorization_code","code":code,"redirect_uri":redirect_uri,"client_id":self.client_id,"client_secret":self.client_secret,"code_verifier":code_verifier}, timeout=self.timeout, allow_redirects=False)
            if response.status_code != 200: raise OidcTokenExchangeError("oidc_exchange_failed")
            payload = response.json()
            if not isinstance(payload, dict): raise OidcTokenExchangeError("oidc_token_response_invalid")
            return payload
        except OidcTokenExchangeError: raise
        except Exception as exc: raise OidcTokenExchangeError("oidc_exchange_failed") from exc
