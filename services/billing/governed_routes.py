"""Fail-closed Flask adapters for the governed billing application boundary."""
from flask import Blueprint, g, jsonify, request, session
from .application import BillingApplicationService, CheckoutRequest
from .exceptions import BillingError, BillingConfigurationError

def create_governed_billing_blueprint(application: BillingApplicationService, context_provider=None, authorization_provider=None, webhook_tenant_provider=None):
    if not isinstance(application,BillingApplicationService) or not callable(context_provider) or not callable(getattr(authorization_provider,"require",None)): return None
    api=Blueprint("governed_billing",__name__,url_prefix="/api/billing/v2")
    def context(): return context_provider()
    def error(exc):
        code="BILLING_NOT_CONFIGURED" if isinstance(exc,BillingConfigurationError) else "AUTHORIZATION_DENIED" if "tenant" in str(exc) or "context" in str(exc) else "INVALID_REQUEST"
        return jsonify({"error":code}),503 if code=="BILLING_NOT_CONFIGURED" else 403 if code=="AUTHORIZATION_DENIED" else 400
    @api.post("/checkout")
    def checkout():
        if not session.get("csrf_token") or request.headers.get("X-CSRF-Token") != session.get("csrf_token"): return jsonify({"error":"csrf_validation_failed"}),403
        payload=request.get_json(silent=True)
        if not isinstance(payload,dict) or set(payload)-{"plan_id","idempotency_key"} or not isinstance(payload.get("plan_id"),str): return jsonify({"error":"INVALID_REQUEST"}),400
        try:
            ctx=context(); authorization_provider.require(ctx,ctx.tenant_id,"billing.checkout")
            result=application.create_checkout_request(ctx,CheckoutRequest(payload["plan_id"],str(payload.get("email","")),str(payload.get("idempotency_key",""))))
            return jsonify({"transaction_reference":result.transaction_reference,"plan_id":result.plan_id,"amount_minor":result.amount_minor,"currency":result.currency,"authorization_url":result.authorization_url})
        except Exception as exc: return error(exc)
    @api.get("/status")
    def status():
        try:
            ctx=context(); authorization_provider.require(ctx,ctx.tenant_id,"billing.status"); value=application.get_billing_status(ctx); return jsonify({"tenant_id":value.tenant_id,"subscription_status":value.subscription_status,"plan_id":value.plan_id,"entitlements":sorted(value.entitlement_capabilities),"transaction_reference":value.transaction_reference,"transaction_status":value.transaction_status})
        except Exception as exc: return error(exc)
    if callable(webhook_tenant_provider):
        @api.post("/webhooks/paystack")
        def webhook():
            try: return jsonify({"accepted":bool(application.process_verified_webhook(request.headers.get("x-paystack-signature",""),request.get_data(cache=False),webhook_tenant_provider()))})
            except Exception: return jsonify({"error":"INVALID_WEBHOOK"}),400
    return api
