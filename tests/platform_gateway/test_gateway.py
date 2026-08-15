from services.platform_gateway import *

class Service:
    def get(self, value=None, *, tenant_id=None): return {"value": value, "tenant_id": tenant_id}

def test_models_serialize():
    assert APIResponse(True, {"x": 1}, request_id="r").to_dict()["success"]

def test_gateway_enforces_tenant_and_delegates():
    registry = GatewayServiceRegistry(); registry.register("demo", Service())
    gateway = PlatformGateway(registry=registry)
    ctx = APIRequestContext("r", "t", "u", "viewer")
    assert gateway.dispatch(ctx, "demo", "get", "ok", tenant_id="t").data["tenant_id"] == "t"
    assert not gateway.dispatch(ctx, "demo", "get", tenant_id="other").success

def test_missing_tenant_denied_and_audited():
    gateway = PlatformGateway(); result = gateway.dispatch(APIRequestContext("r", None), "demo", "get")
    assert not result.success and result.error == "tenant_required"
    assert gateway.audit.events[-1]["event_type"] == "gateway_request_denied"

def test_development_auth_is_explicit():
    try: DevelopmentAuthenticationProvider().authenticate({"tenant_id": "t"})
    except PermissionError: pass
    else: assert False
    assert DevelopmentAuthenticationProvider(True).authenticate({"tenant_id": "t"}).role == "viewer"
