from services.identity.oidc_browser import OidcAuthorizationCodeFlow, OidcBrowserConfiguration, OidcBrowserError, _challenge
from tests.credential_helpers import random_token


ID_TOKEN = random_token()

class TokenClient:
    def exchange(self, code, redirect_uri, verifier): self.args=(code,redirect_uri,verifier); return {"token_type":"Bearer","id_token":ID_TOKEN}
class Adapter:
    def authenticate(self, token, state, nonce, verifier): self.args=(token,state,nonce,verifier); return type("P",(),{"provider":"entra","external_subject":"subject","tenant_id":"tenant","actor_id":"actor"})()

def flow(): return OidcAuthorizationCodeFlow(OidcBrowserConfiguration("https://idp.example/authorize","https://app.example/auth/callback","client"),Adapter(),TokenClient())
def test_begin_generates_state_nonce_and_pkce():
    session={}; url=flow().begin(session); assert session["oidc_transaction"]["state"] in url and "code_challenge_method=S256" in url
def test_complete_consumes_transaction_and_establishes_minimal_session():
    f=flow(); session={}; f.begin(session); state=session["oidc_transaction"]["state"]; principal=f.complete(session,{"state":state,"code":"code"}); assert principal.actor_id=="actor" and "oidc_transaction" not in session
def test_invalid_state_and_missing_code_fail_closed():
    f=flow(); session={}; f.begin(session)
    try: f.complete(session,{"state":"wrong","code":"code"}); assert False
    except OidcBrowserError: pass
    session={}; f.begin(session); state=session["oidc_transaction"]["state"]
    try: f.complete(session,{"state":state}); assert False
    except OidcBrowserError: pass
def test_logout_clears_local_session():
    session={"canonical_principal":{"actor_id":"a"},"oidc_transaction":{"state":"s"}}; OidcAuthorizationCodeFlow.logout(session); assert session=={}
