"""Fail-closed readiness for governed billing route registration."""
from dataclasses import dataclass

def evaluate_crypto_sandbox(*, validator=None):
    """Explicit readiness operation; never called by route or container setup."""
    if validator is None:
        return {"state": "BLOCKED", "reason": "CRYPTO_CONFIGURATION_INCOMPLETE"}
    return validator.validate().as_dict()

@dataclass(frozen=True)
class PaystackOperationalReadiness:
    state: str
    ready: bool
    production_approved: bool
    reason: str
    checks: tuple[tuple[str, str], ...]

    def as_dict(self):
        return {"state": self.state, "ready": self.ready, "production_approved": self.production_approved, "reason": self.reason, "checks": dict(self.checks)}

def evaluate_paystack_operations(*, configuration, secret_available, provider_validation=None, webhook_trust=False, authorization=False, production_approval=False):
    checks = {
        "configuration": "PASS" if configuration and configuration.reason_codes() == ("PAYSTACK_READY",) else "BLOCKED",
        "secret": "PASS" if secret_available else "BLOCKED",
        "provider_api": "PASS" if provider_validation and provider_validation.state == "PROVIDER_VALIDATED" else "BLOCKED",
        "webhook": "PASS" if webhook_trust else "BLOCKED",
        "authorization": "PASS" if authorization else "BLOCKED",
        "route_registration": "PASS" if production_approval else "BLOCKED",
        "production_approval": "PASS" if production_approval else "BLOCKED",
    }
    if not configuration or configuration.reason_codes() == ("PAYSTACK_DISABLED",):
        return PaystackOperationalReadiness("DISABLED", False, False, "paystack_disabled", tuple(checks.items()))
    if not all(value == "PASS" for key, value in checks.items() if key not in {"route_registration", "production_approval"}):
        return PaystackOperationalReadiness("ROUTE_REGISTRATION_BLOCKED", False, False, "production_prerequisites_incomplete", tuple(checks.items()))
    if not production_approval:
        return PaystackOperationalReadiness("PROVIDER_VALIDATED", True, False, "production_not_approved", tuple(checks.items()))
    return PaystackOperationalReadiness("PRODUCTION_READY", True, True, "production_approved", tuple(checks.items()))

@dataclass(frozen=True)
class BillingRouteReadiness:
    state: str
    ready: bool
    reasons: tuple[str,...]
    checkout_ready: bool
    status_ready: bool
    webhook_ready: bool

class BillingRouteReadinessEvaluator:
    def evaluate(self, *, billing_application=None, billing_service=None, repository=None, context_provider=None, authorization_provider=None, csrf_validator=None, webhook_verifier=None, webhook_tenant_resolver=None, payment_provider=None, secret_reference=None, billing_configuration=None, crypto_configuration=None, crypto_provider=None):
        reasons=[]
        if billing_application is None: reasons.append("billing_application_unavailable")
        if billing_service is None: reasons.append("billing_service_unavailable")
        if repository is None: reasons.append("billing_repository_unavailable")
        if not callable(context_provider): reasons.append("canonical_request_context_unavailable")
        if not callable(authorization_provider): reasons.append("canonical_authorization_unavailable")
        if not callable(csrf_validator): reasons.append("csrf_protection_unavailable")
        if not callable(webhook_verifier): reasons.append("webhook_verifier_unavailable")
        if not callable(webhook_tenant_resolver): reasons.append("webhook_tenant_resolver_unavailable")
        config_ready=False
        if billing_configuration is not None:
            try:
                config_ready=bool(billing_configuration.validate())
                if not config_ready: reasons.append("billing_configuration_incomplete")
            except Exception: reasons.append("billing_configuration_invalid")
        if not payment_provider: reasons.append("payment_provider_unavailable")
        if not secret_reference: reasons.append("billing_secret_reference_unavailable")
        if crypto_configuration is not None and crypto_configuration.reason_codes() != ("CRYPTO_DISABLED",):
            if crypto_configuration.reason_codes() != ("CRYPTO_READY",): reasons.append(crypto_configuration.reason_codes()[0])
            if crypto_provider is None: reasons.append("crypto_provider_unavailable")
        checkout=not reasons
        status=not any(x in reasons for x in ("billing_application_unavailable","billing_service_unavailable","billing_repository_unavailable","canonical_request_context_unavailable","canonical_authorization_unavailable"))
        webhook=not any(x in reasons for x in ("billing_application_unavailable","repository_unavailable","billing_repository_unavailable","webhook_verifier_unavailable","webhook_tenant_resolver_unavailable"))
        if not config_ready: checkout=False
        return BillingRouteReadiness("READY_FOR_CONTROLLED_ROUTE_REGISTRATION" if checkout and status and webhook else "ROUTE_REGISTRATION_BLOCKED", checkout and status and webhook, tuple(dict.fromkeys(reasons)), checkout, status, webhook)

def register_if_ready(app, blueprint, readiness: BillingRouteReadiness):
    if readiness.ready and blueprint is not None: app.register_blueprint(blueprint); return True
    return False
