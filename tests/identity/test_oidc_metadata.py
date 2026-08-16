from services.identity.oidc_metadata import OidcMetadataValidator
from services.identity.oidc_config import OidcRuntimeConfiguration

def cfg(**changes):
    v=dict(provider="p",issuer="https://issuer.example",authorization_endpoint="https://issuer.example/auth",token_endpoint="https://issuer.example/token",jwks_uri="https://issuer.example/jwks",client_id="c",audience="a",redirect_uri="https://app.example/cb",client_secret_reference="S",provider_tenant_claim="tid",signing_algorithms=("RS256",),external_tenant_id="e"); v.update(changes); return OidcRuntimeConfiguration(**v)
def docs(config=None, keys=None):
    c=config or cfg(); return {"issuer":c.issuer,"authorization_endpoint":c.authorization_endpoint,"token_endpoint":c.token_endpoint,"jwks_uri":c.jwks_uri,"id_token_signing_alg_values_supported":["RS256"]}, {"keys": keys or [{"kty":"RSA","kid":"k1","alg":"RS256","n":"n","e":"e"}]}
def test_valid_discovery_and_jwks():
    d,j=docs(); result=OidcMetadataValidator(lambda url,**kwargs: (200, __import__("json").dumps(d if url.endswith("configuration") else j))).validate(cfg()); assert result.valid and result.signing_key_count==1
def test_issuer_and_endpoint_mismatch_fail():
    d,j=docs(); d["issuer"]="https://other.example"; result=OidcMetadataValidator(lambda url,**kwargs:(200,__import__("json").dumps(d if url.endswith("configuration") else j))).validate(cfg()); assert not result.valid
def test_private_endpoint_and_duplicate_kid_fail():
    d,j=docs(); assert not OidcMetadataValidator(lambda *a,**k:(200,"{}")).validate(cfg(jwks_uri="https://127.0.0.1/jwks")).valid; j["keys"].append(j["keys"][0].copy()); result=OidcMetadataValidator(lambda url,**kwargs:(200,__import__("json").dumps(d if url.endswith("configuration") else j))).validate(cfg()); assert not result.valid
