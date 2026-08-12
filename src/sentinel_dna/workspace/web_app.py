import logging
import time

from flask import Flask, abort, g, jsonify, redirect, render_template_string, request, url_for

from sentinel_dna.case_management.case_store import CaseStore
from sentinel_dna.evidence.evidence_engine import EvidenceEngine
from sentinel_dna.investigation.reporting import InvestigationReporter
from sentinel_dna.risk.risk_engine import RiskEngine
from sentinel_dna.investigation.analyst_actions import AnalystActionService
from sentinel_dna.config import SentinelDNASettings
from sentinel_dna.saas.auth import AuthService, AuthenticationError, AuthorizationError
from sentinel_dna.saas.billing import BillingConfigurationError, BillingService, EntitlementError
from sentinel_dna.saas.identity import IdentityStore, Role
from sentinel_dna.saas.stripe_provider import StripeConfig, StripeProvider, StripeSignatureError
from sentinel_dna.saas.usage import UsageMeter
from sentinel_dna import __version__
from sentinel_dna.observability import ServiceMetrics, configure_logging
from sentinel_dna.platform.distributed import LocalRateLimitStore, RedisRateLimitStore


PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Sentinel DNA v1.0 Beta</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 40px;
      background: #0f172a;
      color: #e2e8f0;
    }

    .card {
      background: #111827;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
    }

    .risk {
      color: #fbbf24;
      font-weight: bold;
    }
  </style>
</head>
<body>
  <h1>Sentinel DNA v1.0 Beta Analyst Workspace</h1>
  <p>Investigations: {{ investigations|length }} · Open: {{ investigations|selectattr('case.status', 'equalto', 'open')|list|length }}</p>

  {% for item in investigations %}
    <section class="card">
      <h2>{{ item.case.title }}</h2>

      <p>{{ item.case.description }}</p>

      <p class="risk">
        Risk: {{ item.risk.level|upper }} {{ item.risk.score }}/100
      </p>

      <p>{{ item.summary.executive_summary }}</p>
      <p>Confidence: {{ item.confidence }} · Status: {{ item.case.status|upper }}</p>
      <p><a href="{{ url_for('detail', case_id=item.case.case_id) }}">Open investigation</a></p>

      <h3>Recommended Actions</h3>

      <ul>
        {% for action in item.summary.recommended_actions %}
          <li>{{ action }}</li>
        {% endfor %}
      </ul>
    </section>
  {% else %}
    <section class="card">
      No cases yet. Run the CLI demo to create a sample investigation.
    </section>
  {% endfor %}
</body>
</html>
"""

DETAIL_PAGE = """
<!doctype html><html><head><meta charset="utf-8"><title>{{ case.case_id }}</title>
<style>body{font-family:Arial;margin:40px;background:#0f172a;color:#e2e8f0}.card{background:#111827;border:1px solid #334155;border-radius:12px;padding:18px;margin:14px 0}a{color:#93c5fd}textarea,input,select,button{padding:8px;margin:4px}</style></head>
<body><a href="{{ url_for('index') }}">← Dashboard</a><h1>{{ case.title }}</h1>
<div class="card"><b>Case:</b> {{ case.case_id }} · <b>Severity:</b> {{ case.severity }} · <b>Status:</b> {{ case.status }}<p>{{ case.description }}</p></div>
<div class="card"><h2>Evidence</h2>{% for e in evidence %}<p>{{ e.summary }} — confidence {{ e.confidence }}<br>Indicators: {{ e.indicators|join(', ') }}</p>{% else %}<p>No evidence.</p>{% endfor %}</div>
<div class="card"><h2>Analyst actions</h2><form method="post" action="{{ url_for('action', case_id=case.case_id) }}"><input name="analyst" placeholder="Analyst name" required><select name="action"><option value="confirm_finding">Confirm finding</option><option value="dismiss_finding">Dismiss finding</option><option value="escalate">Escalate</option><option value="add_note">Add note</option></select><textarea name="note" placeholder="Analyst note"></textarea><button>Record action</button></form></div>
<div class="card"><h2>Audit history</h2>{% for event in case.events %}<p>{{ event.timestamp }} · {{ event.event_type }} · {{ event.message }}</p>{% endfor %}</div></body></html>
"""


class ResilientRateLimitStore:
    def __init__(self, primary, fallback=None, logger=None) -> None:
        self.primary = primary
        self.fallback = fallback or LocalRateLimitStore()
        self.logger = logger or logging.getLogger("sentinel_dna.web")

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        try:
            return self.primary.allow(key, limit, window_seconds)
        except Exception:
            self.logger.warning("rate_limiter_fallback", extra={"event_type": "operations"})
            return self.fallback.allow(key, limit, window_seconds)


def rate_limit_key() -> str:
    tenant_id = request.headers.get("X-Sentinel-Org") or request.args.get("tenant_id")
    if tenant_id:
        return f"tenant:{tenant_id}"
    return f"ip:{request.remote_addr or 'unknown'}"


def select_rate_limiter(settings: SentinelDNASettings, logger=None):
    if settings.redis_url:
        try:
            return ResilientRateLimitStore(RedisRateLimitStore(settings.redis_url), logger=logger)
        except Exception:
            (logger or logging.getLogger("sentinel_dna.web")).warning("rate_limiter_startup_fallback", extra={"event_type": "operations"})
    return LocalRateLimitStore()


def create_app(data_dir: str | None = None, billing_provider=None) -> Flask:
    configure_logging()
    app = Flask(__name__)
    settings = SentinelDNASettings.from_environment()
    resolved_data_dir = data_dir or settings.data_dir
    # Explicitly keep debug mode off unless an operator opts in for local development.
    app.config.update(JSON_SORT_KEYS=False)
    logger = logging.getLogger("sentinel_dna.web")
    metrics = ServiceMetrics()
    rate_limiter = select_rate_limiter(settings, logger)
    auth_service = AuthService(resolved_data_dir)
    identity_store = IdentityStore(resolved_data_dir)
    usage_meter = UsageMeter(resolved_data_dir)
    if billing_provider is None and (settings.stripe_secret_key or settings.stripe_webhook_secret or settings.stripe_price_ids):
        billing_provider = StripeProvider(StripeConfig(settings.stripe_secret_key, settings.stripe_webhook_secret, settings.stripe_price_ids))
    billing_service = BillingService(resolved_data_dir, provider=billing_provider)

    def bearer_token() -> str | None:
        header = request.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            return header.split(" ", 1)[1].strip()
        return None

    def json_object() -> dict:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def active_principal():
        return auth_service.authenticate_token(bearer_token())

    def optional_principal():
        token = bearer_token()
        if not token:
            return None
        return auth_service.authenticate_token(token)

    def active_tenant_id() -> str:
        tenant_id = request.headers.get("X-Sentinel-Org") or request.args.get("tenant_id")
        if not tenant_id:
            raise AuthorizationError("tenant context required")
        return tenant_id

    def idempotency_key() -> str:
        key = request.headers.get("Idempotency-Key")
        if not key:
            payload = json_object()
            key = payload.get("idempotency_key")
        if not key:
            raise ValueError("idempotency key required")
        return key

    def public_user(user):
        return {
            "user_id": user.user_id,
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }

    def public_record(record):
        return record.__dict__ if record else None

    @app.errorhandler(AuthenticationError)
    def authentication_failed(_exc):
        logger.warning("authentication_denied", extra={"event_type": "security_audit"})
        return jsonify({"error": "authentication_required"}), 401

    @app.errorhandler(AuthorizationError)
    def authorization_failed(_exc):
        logger.warning("authorization_denied", extra={"event_type": "security_audit"})
        return jsonify({"error": "access_denied"}), 403

    @app.errorhandler(ValueError)
    def bad_request(_exc):
        return jsonify({"error": "invalid_request"}), 400

    @app.errorhandler(EntitlementError)
    def entitlement_failed(_exc):
        return jsonify({"error": "entitlement_required"}), 402

    @app.errorhandler(BillingConfigurationError)
    def billing_not_configured(_exc):
        return jsonify({"error": "billing_provider_not_configured"}), 503

    @app.errorhandler(StripeSignatureError)
    def stripe_signature_failed(_exc):
        return jsonify({"error": "invalid_webhook_signature"}), 400

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'"
        duration_ms = round((time.perf_counter() - getattr(g, "request_started", time.perf_counter())) * 1000, 2)
        metrics.record_request(request.method, response.status_code)
        logger.info("http_request", extra={"event_type": "api_request", "method": request.method, "path": request.path, "status_code": response.status_code, "duration_ms": duration_ms})
        return response

    @app.before_request
    def start_request_timer():
        g.request_started = time.perf_counter()
        if not rate_limiter.allow(rate_limit_key(), settings.rate_limit_per_minute, 60):
            return jsonify({"error": "rate_limited"}), 429

    @app.get("/healthz")
    def healthz():
        try:
            CaseStore(resolved_data_dir)
            auth_service.database.is_ready()
            return jsonify({"status": "ok", "service": "sentinel-dna", "version": "1.0-beta"})
        except Exception:
            logger.exception("Health check storage failure")
            return jsonify({"status": "degraded", "service": "sentinel-dna", "error": "storage_unavailable"}), 503

    @app.get("/readyz")
    def readyz():
        try:
            CaseStore(resolved_data_dir)
            auth_service.database.is_ready()
            return jsonify({"status": "ready"})
        except Exception:
            logger.exception("Readiness check storage failure")
            return jsonify({"status": "not_ready", "error": "storage_unavailable"}), 503

    @app.get("/version")
    def version():
        return jsonify({"service": "sentinel-dna", "version": __version__})

    @app.get("/metrics")
    def metric_endpoint():
        if settings.metrics_private:
            supplied_token = request.headers.get("X-Sentinel-Metrics-Token")
            auth_header = request.headers.get("Authorization", "")
            if not supplied_token and auth_header.lower().startswith("bearer "):
                supplied_token = auth_header.split(" ", 1)[1].strip()
            if supplied_token != settings.metrics_token:
                raise AuthorizationError("metrics access denied")
        return app.response_class(metrics.prometheus(), mimetype="text/plain; version=0.0.4; charset=utf-8")

    @app.post("/auth/register")
    def register():
        payload = json_object()
        try:
            registration = auth_service.register(
                payload.get("email", ""),
                payload.get("password", ""),
                payload.get("display_name", ""),
                payload.get("organization_name"),
            )
        except ValueError as exc:
            logger.info("registration_rejected", extra={"event_type": "security_audit"})
            return jsonify({"error": "registration_failed"}), 400
        response = {"user": public_user(registration["user"])}
        if registration["organization"]:
            response["organization"] = {
                "organization_id": registration["organization"].organization_id,
                "name": registration["organization"].name,
                "created_at": registration["organization"].created_at,
            }
            response["membership"] = {
                "membership_id": registration["membership"].membership_id,
                "role": registration["membership"].role.value,
            }
        return jsonify(response), 201

    @app.post("/auth/login")
    def login():
        payload = json_object()
        principal = auth_service.login(payload.get("email", ""), payload.get("password", ""))
        logger.info("login_succeeded", extra={"event_type": "security_audit"})
        return jsonify({"token": principal.token, "user": public_user(principal.user)})

    @app.post("/auth/logout")
    def logout():
        token = bearer_token()
        auth_service.authenticate_token(token)
        auth_service.revoke_token(token)
        logger.info("logout_succeeded", extra={"event_type": "security_audit"})
        return "", 204

    @app.get("/auth/me")
    def me():
        principal = active_principal()
        return jsonify({
            "user": public_user(principal.user),
            "organizations": identity_store.list_user_organizations(principal.user.user_id),
        })

    @app.post("/organizations")
    def create_organization():
        principal = active_principal()
        payload = json_object()
        try:
            organization = identity_store.create_organization(payload.get("name", ""))
            membership = identity_store.create_membership(principal.user.user_id, organization.organization_id, Role.OWNER)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({
            "organization": {
                "organization_id": organization.organization_id,
                "name": organization.name,
                "created_at": organization.created_at,
            },
            "membership": {"membership_id": membership.membership_id, "role": membership.role.value},
        }), 201

    @app.get("/organizations")
    def list_organizations():
        principal = active_principal()
        return jsonify({"organizations": identity_store.list_user_organizations(principal.user.user_id)})

    @app.get("/organizations/<organization_id>")
    def get_organization(organization_id: str):
        principal = active_principal()
        auth_service.require_tenant_access(principal.user.user_id, organization_id)
        organization = identity_store.get_organization(organization_id)
        if not organization:
            abort(404)
        return jsonify({
            "organization_id": organization.organization_id,
            "name": organization.name,
            "created_at": organization.created_at,
        })

    @app.get("/organizations/<organization_id>/members")
    def list_members(organization_id: str):
        principal = active_principal()
        auth_service.require_minimum_role(principal.user.user_id, organization_id, Role.VIEWER)
        return jsonify({"members": identity_store.list_members(organization_id)})

    @app.post("/organizations/<organization_id>/members")
    def add_member(organization_id: str):
        principal = active_principal()
        actor_membership = auth_service.require_role(principal.user.user_id, organization_id, Role.OWNER, Role.ADMIN)
        payload = json_object()
        try:
            user = identity_store.get_user_by_email(payload.get("email", ""))
        except ValueError:
            return jsonify({"error": "user_not_found"}), 404
        if user is None:
            return jsonify({"error": "user_not_found"}), 404
        try:
            requested_role = Role(payload.get("role", Role.VIEWER))
            if actor_membership.role != Role.OWNER and requested_role == Role.OWNER:
                raise AuthorizationError("only an owner may grant the owner role")
            membership = identity_store.create_membership(user.user_id, organization_id, requested_role)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"membership_id": membership.membership_id, "user_id": user.user_id, "role": membership.role.value}), 201

    @app.get("/usage")
    def usage():
        principal = active_principal()
        tenant_id = active_tenant_id()
        auth_service.require_tenant_access(principal.user.user_id, tenant_id)
        return jsonify({
            "usage": [
                event.__dict__
                for event in usage_meter.get_usage(
                    tenant_id,
                    start=request.args.get("start"),
                    end=request.args.get("end"),
                )
            ]
        })

    @app.get("/usage/<metric>")
    def usage_metric(metric: str):
        principal = active_principal()
        tenant_id = active_tenant_id()
        auth_service.require_tenant_access(principal.user.user_id, tenant_id)
        return jsonify({
            "metric": metric,
            "totals": usage_meter.aggregate_usage(
                tenant_id,
                metric,
                start=request.args.get("start"),
                end=request.args.get("end"),
            ),
        })

    @app.get("/billing/plans")
    def billing_plans():
        principal = active_principal()
        tenant_id = active_tenant_id()
        auth_service.require_tenant_access(principal.user.user_id, tenant_id)
        return jsonify({"plans": [public_record(plan) for plan in billing_service.list_plans()]})

    @app.get("/billing/customer")
    def billing_customer():
        principal = active_principal()
        tenant_id = active_tenant_id()
        auth_service.require_minimum_role(principal.user.user_id, tenant_id, Role.VIEWER)
        return jsonify({"customer": public_record(billing_service.get_customer(tenant_id))})

    @app.post("/billing/customer")
    def create_billing_customer():
        principal = active_principal()
        tenant_id = active_tenant_id()
        auth_service.require_role(principal.user.user_id, tenant_id, Role.OWNER, Role.ADMIN)
        payload = json_object()
        customer = billing_service.create_customer(tenant_id, payload.get("billing_email", ""), idempotency_key())
        return jsonify({"customer": public_record(customer)}), 201

    @app.get("/billing/subscription")
    def billing_subscription():
        principal = active_principal()
        tenant_id = active_tenant_id()
        auth_service.require_minimum_role(principal.user.user_id, tenant_id, Role.VIEWER)
        return jsonify({"subscription": public_record(billing_service.get_subscription(tenant_id))})

    @app.post("/billing/subscription")
    def create_billing_subscription():
        principal = active_principal()
        tenant_id = active_tenant_id()
        auth_service.require_role(principal.user.user_id, tenant_id, Role.OWNER, Role.ADMIN)
        payload = json_object()
        subscription = billing_service.create_subscription(tenant_id, payload.get("plan_id", ""), idempotency_key())
        return jsonify({"subscription": public_record(subscription)}), 201

    @app.delete("/billing/subscription")
    def cancel_billing_subscription():
        principal = active_principal()
        tenant_id = active_tenant_id()
        auth_service.require_role(principal.user.user_id, tenant_id, Role.OWNER, Role.ADMIN)
        subscription = billing_service.cancel_subscription(tenant_id, idempotency_key())
        return jsonify({"subscription": public_record(subscription)})

    @app.post("/billing/checkout")
    def billing_checkout():
        principal = active_principal()
        tenant_id = active_tenant_id()
        auth_service.require_role(principal.user.user_id, tenant_id, Role.OWNER, Role.ADMIN)
        payload = json_object()
        session = billing_service.start_checkout(tenant_id, payload.get("plan_id", ""), idempotency_key())
        return jsonify({"checkout_url": session.get("url"), "checkout_session_id": session.get("id")})

    @app.get("/billing/invoices")
    def billing_invoices():
        principal = active_principal()
        tenant_id = active_tenant_id()
        auth_service.require_minimum_role(principal.user.user_id, tenant_id, Role.VIEWER)
        return jsonify({"invoices": [public_record(invoice) for invoice in billing_service.list_invoices(tenant_id)]})

    @app.post("/billing/invoices")
    def create_billing_invoice():
        principal = active_principal()
        tenant_id = active_tenant_id()
        auth_service.require_role(principal.user.user_id, tenant_id, Role.OWNER, Role.ADMIN)
        invoice = billing_service.create_invoice(tenant_id, idempotency_key())
        return jsonify({"invoice": public_record(invoice)}), 201

    @app.post("/billing/webhook")
    def billing_webhook():
        event = billing_service.provider.verify_webhook_signature(
            request.get_data(),
            request.headers.get("Stripe-Signature"),
        )
        event_id = event["id"]
        event_type = event["type"]
        data_object = event.get("data", {}).get("object", {})
        tenant_id = _stripe_tenant_id(data_object)
        if not billing_service.record_provider_event(event_id, event_type, tenant_id, event):
            return jsonify({"status": "duplicate"})
        _process_stripe_event(event_type, data_object, event_id)
        return jsonify({"status": "processed"})

    def _stripe_tenant_id(data_object):
        metadata = data_object.get("metadata") or {}
        tenant_id = metadata.get("tenant_id") or data_object.get("client_reference_id")
        if not tenant_id and data_object.get("subscription_details"):
            tenant_id = (data_object.get("subscription_details", {}).get("metadata") or {}).get("tenant_id")
        return tenant_id

    def _stripe_plan_id(data_object):
        metadata = data_object.get("metadata") or {}
        return metadata.get("plan_id") or (data_object.get("subscription_details", {}).get("metadata") or {}).get("plan_id")

    def _process_stripe_event(event_type: str, data_object: dict, event_id: str) -> None:
        if event_type == "checkout.session.completed":
            tenant_id = _stripe_tenant_id(data_object)
            plan_id = _stripe_plan_id(data_object)
            subscription_id = data_object.get("subscription")
            if tenant_id and plan_id and subscription_id:
                billing_service.apply_provider_subscription(tenant_id, plan_id, "active", subscription_id, f"{event_id}:subscription")
            return
        if event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
            tenant_id = _stripe_tenant_id(data_object)
            plan_id = _stripe_plan_id(data_object)
            provider_subscription_id = data_object.get("id")
            status = "canceled" if event_type == "customer.subscription.deleted" else data_object.get("status", "incomplete")
            if tenant_id and plan_id and provider_subscription_id:
                billing_service.apply_provider_subscription(tenant_id, plan_id, status, provider_subscription_id, f"{event_id}:subscription", metadata=data_object)
            return
        if event_type in {"invoice.paid", "invoice.payment_failed"}:
            tenant_id = _stripe_tenant_id(data_object)
            if tenant_id:
                invoice = dict(data_object)
                invoice["status"] = "paid" if event_type == "invoice.paid" else "payment_failed"
                billing_service.apply_provider_invoice(tenant_id, invoice, f"{event_id}:invoice")

    @app.get("/")
    def index():
        case_store = CaseStore(resolved_data_dir)
        evidence_engine = EvidenceEngine(resolved_data_dir)
        risk_engine = RiskEngine()
        reporter = InvestigationReporter()

        investigations = []

        principal = optional_principal()
        tenant_id = request.headers.get("X-Sentinel-Org") or request.args.get("tenant_id")
        if tenant_id:
            if principal is None:
                raise AuthenticationError("authentication required")
            auth_service.require_tenant_access(principal.user.user_id, tenant_id)
            cases = case_store.list_cases_for_tenant(tenant_id)
        else:
            cases = [case for case in case_store.list_cases() if case.tenant_id is None]

        for case in cases:
            evidence_items = [
                evidence_engine.get(evidence_id)
                for evidence_id in case.evidence_ids
            ]

            risk = risk_engine.assess(evidence_items)

            summary = reporter.summarize(
                case,
                evidence_items,
                risk,
            )

            investigations.append(
                {
                    "case": case,
                    "risk": risk,
                    "summary": summary,
                    "confidence": "evidence-backed",
                }
            )

        return render_template_string(
            PAGE,
            investigations=investigations,
        )

    @app.get("/investigations/<case_id>")
    def detail(case_id: str):
        case_store = CaseStore(resolved_data_dir)
        evidence_engine = EvidenceEngine(resolved_data_dir)
        try:
            case = case_store.get(case_id)
        except FileNotFoundError:
            abort(404)
        if case.tenant_id is not None:
            principal = active_principal()
            tenant_id = active_tenant_id()
            if tenant_id != case.tenant_id:
                raise AuthorizationError("access denied")
            auth_service.require_tenant_access(principal.user.user_id, tenant_id)
        evidence = [evidence_engine.get(evidence_id) for evidence_id in case.evidence_ids]
        return render_template_string(DETAIL_PAGE, case=case, evidence=evidence)

    @app.post("/investigations/<case_id>/actions")
    def action(case_id: str):
        try:
            case = CaseStore(resolved_data_dir).get(case_id)
        except FileNotFoundError:
            abort(404)
        if case.tenant_id is not None:
            principal = active_principal()
            tenant_id = active_tenant_id()
            if tenant_id != case.tenant_id:
                raise AuthorizationError("access denied")
            auth_service.require_minimum_role(principal.user.user_id, tenant_id, Role.ANALYST)
        try:
            AnalystActionService(resolved_data_dir).record(
                case_id, request.form.get("action", ""), request.form.get("analyst", ""), request.form.get("note", ""),
            )
        except ValueError as exc:
            abort(400, description=str(exc))
        return redirect(url_for("detail", case_id=case_id))

    return app


if __name__ == "__main__":
    runtime_settings = SentinelDNASettings.from_environment()
    create_app(runtime_settings.data_dir).run(
        host=runtime_settings.host,
        port=runtime_settings.port,
        debug=runtime_settings.debug,
    )
