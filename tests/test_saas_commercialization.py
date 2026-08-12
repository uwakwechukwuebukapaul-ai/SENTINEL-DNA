import pytest
import hashlib
import hmac
import json
import time

from sentinel_dna.case_management.case_store import CaseStore
from sentinel_dna.investigation import InvestigationCoordinator
from sentinel_dna.saas.auth import AuthService, AuthenticationError, AuthorizationError, PasswordHasher
from sentinel_dna.saas.billing import BillingConfigurationError, BillingService, EntitlementError
from sentinel_dna.saas.reconciliation import BillingReconciliationWorker
from sentinel_dna.saas.stripe_provider import StripeConfig, StripeProvider
from sentinel_dna.saas.identity import IdentityStore, Role, validate_identifier
from sentinel_dna.saas.investigation_service import TenantInvestigationService
from sentinel_dna.saas.usage import UsageMeter
from sentinel_dna.workspace.web_app import create_app


class FakeStripeHttpClient:
    def __init__(self):
        self.posts = []
        self.deletes = []
        self.subscription_status = "canceled"

    def post(self, path, data, idempotency_key):
        self.posts.append((path, data, idempotency_key))
        if path == "/v1/customers":
            return {"id": "cus_test_123"}
        return {"id": "cs_test_123", "url": "https://checkout.stripe.test/session"}

    def delete(self, path, idempotency_key):
        self.deletes.append((path, idempotency_key))
        return {"id": path.rsplit("/", 1)[-1], "status": "canceled"}

    def get(self, path):
        if path.startswith("/v1/subscriptions/"):
            return {"id": path.rsplit("/", 1)[-1], "status": self.subscription_status}
        return {"data": [{"id": "in_test_123", "status": "paid"}]}


def stripe_provider(secret="whsec_test"):
    return StripeProvider(
        StripeConfig("sk_test", secret, {"plan-free": "price_free", "plan-team": "price_team"}),
        FakeStripeHttpClient(),
    )


def stripe_signature(payload: bytes, secret="whsec_test"):
    timestamp = str(int(time.time()))
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def create_identity(data_dir):
    auth = AuthService(str(data_dir))
    registration = auth.register(
        "owner@example.com",
        "correct horse battery staple",
        "Owner User",
        "Acme SOC",
    )
    return auth, registration["user"], registration["organization"], registration["membership"]


def test_identity_user_organization_membership_and_roles(tmp_path):
    auth, owner, organization, membership = create_identity(tmp_path)
    identity = IdentityStore(str(tmp_path))
    analyst = identity.create_user("analyst@example.com", "Analyst", PasswordHasher.hash_password("analyst password"))
    analyst_membership = identity.create_membership(analyst.user_id, organization.organization_id, Role.ANALYST)

    assert owner.email == "owner@example.com"
    assert organization.organization_id.startswith("org-")
    assert membership.role == Role.OWNER
    assert analyst_membership.role == Role.ANALYST
    assert identity.get_membership(analyst.user_id, organization.organization_id).role == Role.ANALYST
    assert auth.require_role(owner.user_id, organization.organization_id, Role.OWNER).role == Role.OWNER


def test_authentication_success_invalid_password_inactive_user_and_hashing(tmp_path):
    auth, user, _organization, _membership = create_identity(tmp_path)

    principal = auth.login("owner@example.com", "correct horse battery staple")

    assert principal.token
    assert principal.user.user_id == user.user_id
    assert auth.authenticate_token(principal.token).user.email == "owner@example.com"
    assert user.password_hash != "correct horse battery staple"
    assert PasswordHasher.verify("correct horse battery staple", user.password_hash)
    assert int(user.password_hash.split("$")[1]) >= 600_000

    with pytest.raises(AuthenticationError):
        auth.login("owner@example.com", "wrong password")

    identity = IdentityStore(str(tmp_path))
    inactive = identity.create_user("inactive@example.com", "Inactive", PasswordHasher.hash_password("inactive password"), is_active=False)
    assert inactive.is_active is False
    with pytest.raises(AuthenticationError):
        auth.login("inactive@example.com", "inactive password")

    with pytest.raises(AuthenticationError):
        auth.login("missing@example.com", "missing password")

    auth.revoke_token(principal.token)
    with pytest.raises(AuthenticationError):
        auth.authenticate_token(principal.token)


def test_authorization_roles_and_denials(tmp_path):
    auth, owner, organization, _membership = create_identity(tmp_path)
    identity = IdentityStore(str(tmp_path))
    admin = identity.create_user("admin@example.com", "Admin", PasswordHasher.hash_password("admin password"))
    analyst = identity.create_user("analyst@example.com", "Analyst", PasswordHasher.hash_password("analyst password"))
    viewer = identity.create_user("viewer@example.com", "Viewer", PasswordHasher.hash_password("viewer password"))
    outsider = identity.create_user("outsider@example.com", "Outsider", PasswordHasher.hash_password("outsider password"))

    identity.create_membership(admin.user_id, organization.organization_id, Role.ADMIN)
    identity.create_membership(analyst.user_id, organization.organization_id, Role.ANALYST)
    identity.create_membership(viewer.user_id, organization.organization_id, Role.VIEWER)

    assert auth.require_minimum_role(owner.user_id, organization.organization_id, Role.VIEWER)
    assert auth.require_minimum_role(admin.user_id, organization.organization_id, Role.ANALYST)
    assert auth.require_minimum_role(analyst.user_id, organization.organization_id, Role.ANALYST)
    assert auth.require_minimum_role(viewer.user_id, organization.organization_id, Role.VIEWER)

    with pytest.raises(AuthorizationError):
        auth.require_minimum_role(viewer.user_id, organization.organization_id, Role.ANALYST)
    with pytest.raises(AuthorizationError):
        auth.require_tenant_access(outsider.user_id, organization.organization_id)


def test_tenant_isolation_for_cases_evidence_and_usage(tmp_path):
    auth, owner, org_a, _membership = create_identity(tmp_path)
    identity = IdentityStore(str(tmp_path))
    org_b = identity.create_organization("Other SOC")
    identity.create_membership(owner.user_id, org_b.organization_id, Role.OWNER)
    service = TenantInvestigationService(tmp_path)
    billing = BillingService(str(tmp_path))
    billing.create_subscription(org_a.organization_id, "plan-free", "tenant-a-subscription-key")
    billing.create_subscription(org_b.organization_id, "plan-free", "tenant-b-subscription-key")

    service.investigate(
        owner.user_id,
        org_a.organization_id,
        "tenant-a-case",
        {"subject": "Verify password", "body": "https://example-login.com"},
    )
    service.investigate(
        owner.user_id,
        org_b.organization_id,
        "tenant-b-case",
        {"subject": "Invoice", "body": "wire details"},
    )

    assert service.get_case(owner.user_id, org_a.organization_id, "tenant-a-case").tenant_id == org_a.organization_id
    with pytest.raises(PermissionError):
        CaseStore(tmp_path).get_for_tenant("tenant-b-case", org_a.organization_id)

    usage = UsageMeter(str(tmp_path))
    assert usage.aggregate_usage(org_a.organization_id)["investigation_completed"] == 1
    assert usage.aggregate_usage(org_b.organization_id)["investigation_completed"] == 1
    usage.assert_tenant(org_a.organization_id, org_a.organization_id)
    with pytest.raises(AuthorizationError):
        usage.assert_tenant(org_b.organization_id, org_a.organization_id)


def test_usage_event_creation_aggregation_date_filtering_and_multiple_metrics(tmp_path):
    meter = UsageMeter(str(tmp_path))
    tenant_id = "org-test"
    before = "2000-01-01T00:00:00+00:00"
    after = "2999-01-01T00:00:00+00:00"

    first = meter.record_event(tenant_id, "api_request", quantity=2, user_id="user-1")
    meter.record_event(tenant_id, "api_request", quantity=3, user_id="user-1")
    meter.record_event(tenant_id, "report_generated", quantity=1, user_id="user-1")
    meter.record_event("org-other", "api_request", quantity=99, user_id="user-2")

    assert first.event_id.startswith("use-")
    assert meter.aggregate_usage(tenant_id)["api_request"] == 5
    assert meter.aggregate_usage(tenant_id)["report_generated"] == 1
    assert meter.aggregate_usage(tenant_id, "api_request") == {"api_request": 5}
    assert meter.get_usage(tenant_id, start=before, end=after)
    assert meter.get_usage(tenant_id, start=after) == []


def test_billing_subscription_lifecycle_idempotency_invoices_and_audit(tmp_path):
    _auth, _owner, organization, _membership = create_identity(tmp_path)
    billing = BillingService(str(tmp_path))

    customer = billing.create_customer(organization.organization_id, "billing@example.com", "customer-key-001")
    duplicate_customer = billing.create_customer(organization.organization_id, "other@example.com", "customer-key-002")
    subscription = billing.create_subscription(organization.organization_id, "plan-free", "subscription-key-001")
    duplicate_subscription = billing.create_subscription(organization.organization_id, "plan-free", "subscription-key-001")
    invoice = billing.create_invoice(organization.organization_id, "invoice-key-001")
    duplicate_invoice = billing.create_invoice(organization.organization_id, "invoice-key-001")

    assert customer.customer_id == duplicate_customer.customer_id
    assert subscription.subscription_id == duplicate_subscription.subscription_id
    assert invoice.invoice_id == duplicate_invoice.invoice_id
    assert billing.get_subscription(organization.organization_id).status == "trialing"
    assert billing.cancel_subscription(organization.organization_id, "cancel-key-001").status == "canceled"
    audit = UsageMeter(str(tmp_path)).aggregate_usage(organization.organization_id)
    assert audit["billing_customer_created"] == 1
    assert audit["subscription_created"] == 1
    assert audit["invoice_created"] == 1
    assert audit["subscription_canceled"] == 1


def test_billing_provider_fails_closed_when_not_configured(tmp_path):
    _auth, _owner, organization, _membership = create_identity(tmp_path)
    billing = BillingService(str(tmp_path))
    with pytest.raises(BillingConfigurationError):
        billing.start_checkout(organization.organization_id, "plan-free", "checkout-key-001")


def test_entitlement_enforcement_requires_active_subscription_and_limits_usage(tmp_path):
    _auth, _owner, organization, _membership = create_identity(tmp_path)
    billing = BillingService(str(tmp_path))
    with pytest.raises(EntitlementError):
        billing.enforce_entitlement(organization.organization_id, "investigation_started")
    billing.create_subscription(organization.organization_id, "plan-free", "subscription-key-002")
    UsageMeter(str(tmp_path)).record_event(organization.organization_id, "investigation_started", quantity=3)
    with pytest.raises(EntitlementError):
        billing.enforce_entitlement(organization.organization_id, "investigation_started")


def test_legacy_organization_slug_is_accepted_but_unsafe_identifiers_are_rejected():
    assert validate_identifier("org-test", "org") == "org-test"
    with pytest.raises(ValueError):
        validate_identifier("org-../other-tenant", "org")


def test_saas_api_auth_organizations_members_and_usage(tmp_path):
    client = create_app(str(tmp_path)).test_client()

    registration = client.post("/auth/register", json={
        "email": "owner@example.com",
        "password": "correct horse battery staple",
        "display_name": "Owner",
        "organization_name": "Acme SOC",
    })
    assert registration.status_code == 201
    tenant_id = registration.json["organization"]["organization_id"]

    login = client.post("/auth/login", json={"email": "owner@example.com", "password": "correct horse battery staple"})
    assert login.status_code == 200
    token = login.json["token"]
    headers = {"Authorization": f"Bearer {token}", "X-Sentinel-Org": tenant_id}

    assert client.get("/auth/me", headers=headers).status_code == 200
    assert client.get("/organizations", headers=headers).json["organizations"]
    assert client.get(f"/organizations/{tenant_id}", headers=headers).status_code == 200
    assert client.get(f"/organizations/{tenant_id}/members", headers=headers).status_code == 200

    UsageMeter(str(tmp_path)).record_event(tenant_id, "api_request", user_id=login.json["user"]["user_id"])
    assert client.get("/usage", headers=headers).status_code == 200
    assert client.get("/usage/api_request", headers=headers).json["totals"] == {"api_request": 1}

    assert client.get("/usage", headers={"Authorization": f"Bearer {token}", "X-Sentinel-Org": "org-not-real"}).status_code == 403
    assert client.get("/version").json["version"]
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_billing_api_auth_role_idempotency_and_not_configured_provider(tmp_path):
    client = create_app(str(tmp_path)).test_client()
    owner = client.post("/auth/register", json={
        "email": "owner@example.com", "password": "correct horse battery staple", "display_name": "Owner", "organization_name": "Acme SOC",
    })
    tenant_id = owner.json["organization"]["organization_id"]
    viewer = client.post("/auth/register", json={
        "email": "viewer@example.com", "password": "correct horse battery staple", "display_name": "Viewer",
    })
    owner_login = client.post("/auth/login", json={"email": "owner@example.com", "password": "correct horse battery staple"})
    owner_headers = {"Authorization": f"Bearer {owner_login.json['token']}", "X-Sentinel-Org": tenant_id}
    assert client.post(f"/organizations/{tenant_id}/members", headers=owner_headers, json={"email": "viewer@example.com", "role": "VIEWER"}).status_code == 201
    viewer_login = client.post("/auth/login", json={"email": "viewer@example.com", "password": "correct horse battery staple"})
    viewer_headers = {"Authorization": f"Bearer {viewer_login.json['token']}", "X-Sentinel-Org": tenant_id}

    assert client.get("/billing/plans", headers=owner_headers).status_code == 200
    assert client.post("/billing/customer", headers=viewer_headers, json={"billing_email": "billing@example.com", "idempotency_key": "customer-api-001"}).status_code == 403
    assert client.post("/billing/customer", headers=owner_headers, json={"billing_email": "billing@example.com", "idempotency_key": "customer-api-001"}).status_code == 201
    first = client.post("/billing/subscription", headers=owner_headers, json={"plan_id": "plan-free", "idempotency_key": "subscription-api-001"})
    second = client.post("/billing/subscription", headers=owner_headers, json={"plan_id": "plan-free", "idempotency_key": "subscription-api-001"})
    assert first.status_code == 201
    assert first.json["subscription"]["subscription_id"] == second.json["subscription"]["subscription_id"]
    assert client.post("/billing/invoices", headers=owner_headers, json={"idempotency_key": "invoice-api-001"}).status_code == 201
    assert client.get("/billing/invoices", headers=viewer_headers).status_code == 200
    assert client.post("/billing/checkout", headers=owner_headers, json={"plan_id": "plan-free", "idempotency_key": "checkout-api-001"}).status_code == 503


def test_stripe_checkout_returns_url_without_activating_subscription(tmp_path):
    provider = stripe_provider()
    client = create_app(str(tmp_path), billing_provider=provider).test_client()
    owner = client.post("/auth/register", json={
        "email": "owner@example.com", "password": "correct horse battery staple", "display_name": "Owner", "organization_name": "Acme SOC",
    })
    tenant_id = owner.json["organization"]["organization_id"]
    login = client.post("/auth/login", json={"email": "owner@example.com", "password": "correct horse battery staple"})
    headers = {"Authorization": f"Bearer {login.json['token']}", "X-Sentinel-Org": tenant_id}

    response = client.post("/billing/checkout", headers=headers, json={"plan_id": "plan-free", "idempotency_key": "checkout-stripe-001"})
    replay = client.post("/billing/checkout", headers=headers, json={"plan_id": "plan-free", "idempotency_key": "checkout-stripe-001"})

    assert response.status_code == 200
    assert response.json["checkout_url"] == "https://checkout.stripe.test/session"
    assert replay.status_code == 200
    assert replay.json == response.json
    assert len(provider.http_client.posts) == 1
    assert BillingService(str(tmp_path), provider=provider).get_subscription(tenant_id) is None


def test_stripe_webhook_rejects_invalid_signature_and_replay(tmp_path):
    provider = stripe_provider()
    client = create_app(str(tmp_path), billing_provider=provider).test_client()
    auth, _owner, organization, _membership = create_identity(tmp_path)
    payload = json.dumps({
        "id": "evt_checkout_1",
        "type": "checkout.session.completed",
        "data": {"object": {"client_reference_id": organization.organization_id, "subscription": "sub_stripe_123", "metadata": {"tenant_id": organization.organization_id, "plan_id": "plan-free"}}},
    }).encode()

    assert client.post("/billing/webhook", data=payload).status_code == 400
    assert client.post("/billing/webhook", data=payload, headers={"Stripe-Signature": "t=1,v1=bad"}).status_code == 400

    signed = {"Stripe-Signature": stripe_signature(payload)}
    first = client.post("/billing/webhook", data=payload, headers=signed)
    second = client.post("/billing/webhook", data=payload, headers=signed)

    assert first.status_code == 200
    assert first.json["status"] == "processed"
    assert second.json["status"] == "duplicate"
    subscription = BillingService(str(tmp_path), provider=provider).get_subscription(organization.organization_id)
    assert subscription.provider_subscription_id == "sub_stripe_123"
    assert subscription.status == "active"


def test_stripe_webhook_handles_subscription_and_invoice_events_idempotently(tmp_path):
    provider = stripe_provider()
    client = create_app(str(tmp_path), billing_provider=provider).test_client()
    _auth, _owner, organization, _membership = create_identity(tmp_path)
    billing = BillingService(str(tmp_path), provider=provider)
    billing.apply_provider_subscription(organization.organization_id, "plan-free", "active", "sub_stripe_123", "seed-subscription-001")
    payload = json.dumps({
        "id": "evt_invoice_1",
        "type": "invoice.payment_failed",
        "data": {"object": {"id": "in_failed_1", "amount_due": 4900, "currency": "usd", "metadata": {"tenant_id": organization.organization_id}}},
    }).encode()

    response = client.post("/billing/webhook", data=payload, headers={"Stripe-Signature": stripe_signature(payload)})
    replay = client.post("/billing/webhook", data=payload, headers={"Stripe-Signature": stripe_signature(payload)})

    assert response.status_code == 200
    assert replay.json["status"] == "duplicate"
    invoices = BillingService(str(tmp_path), provider=provider).list_invoices(organization.organization_id)
    assert invoices[0].provider_invoice_id == "in_failed_1"
    assert invoices[0].status == "payment_failed"


def test_stripe_cross_tenant_access_forged_state_unauthorized_cancel_and_missing_config(tmp_path):
    provider = stripe_provider()
    client = create_app(str(tmp_path), billing_provider=provider).test_client()
    owner = client.post("/auth/register", json={
        "email": "owner@example.com", "password": "correct horse battery staple", "display_name": "Owner", "organization_name": "Acme SOC",
    })
    outsider = client.post("/auth/register", json={
        "email": "outsider@example.com", "password": "correct horse battery staple", "display_name": "Outsider", "organization_name": "Other SOC",
    })
    tenant_id = owner.json["organization"]["organization_id"]
    other_tenant_id = outsider.json["organization"]["organization_id"]
    owner_login = client.post("/auth/login", json={"email": "owner@example.com", "password": "correct horse battery staple"})
    outsider_login = client.post("/auth/login", json={"email": "outsider@example.com", "password": "correct horse battery staple"})
    owner_headers = {"Authorization": f"Bearer {owner_login.json['token']}", "X-Sentinel-Org": tenant_id}
    outsider_headers = {"Authorization": f"Bearer {outsider_login.json['token']}", "X-Sentinel-Org": tenant_id}

    BillingService(str(tmp_path), provider=provider).apply_provider_subscription(tenant_id, "plan-free", "active", "sub_stripe_123", "seed-subscription-002")

    assert client.get("/billing/subscription", headers={"Authorization": f"Bearer {owner_login.json['token']}", "X-Sentinel-Org": other_tenant_id}).status_code == 403
    assert client.delete("/billing/subscription", headers=outsider_headers, json={"idempotency_key": "cancel-denied-001"}).status_code == 403
    forged = client.post("/billing/subscription", headers=owner_headers, json={"plan_id": "plan-free", "status": "active", "provider_subscription_id": "forged", "idempotency_key": "forged-state-001"})
    assert forged.status_code == 400
    with pytest.raises(BillingConfigurationError):
        StripeProvider(StripeConfig("", "whsec_test", {"plan-free": "price_free"}))


def test_reconciliation_worker_audits_stale_provider_state(tmp_path):
    provider = stripe_provider()
    _auth, _owner, organization, _membership = create_identity(tmp_path)
    billing = BillingService(str(tmp_path), provider=provider)
    billing.apply_provider_subscription(organization.organization_id, "plan-free", "active", "sub_stripe_123", "seed-subscription-003")

    findings = BillingReconciliationWorker(billing).reconcile_tenant(organization.organization_id)

    assert {finding.reason for finding in findings} == {"subscription_status_drift", "commercial_access_requires_review"}
    assert UsageMeter(str(tmp_path)).aggregate_usage(organization.organization_id)["billing_reconciliation_required"] == 2


def test_admin_cannot_grant_owner_role(tmp_path):
    client = create_app(str(tmp_path)).test_client()
    owner = client.post("/auth/register", json={
        "email": "owner@example.com", "password": "correct horse battery staple", "display_name": "Owner", "organization_name": "Acme SOC",
    })
    tenant_id = owner.json["organization"]["organization_id"]
    admin_registration = client.post("/auth/register", json={
        "email": "admin@example.com", "password": "correct horse battery staple", "display_name": "Admin",
    })
    owner_login = client.post("/auth/login", json={"email": "owner@example.com", "password": "correct horse battery staple"})
    owner_headers = {"Authorization": f"Bearer {owner_login.json['token']}", "X-Sentinel-Org": tenant_id}
    assert client.post(f"/organizations/{tenant_id}/members", headers=owner_headers, json={"email": "admin@example.com", "role": "ADMIN"}).status_code == 201
    admin_login = client.post("/auth/login", json={"email": "admin@example.com", "password": "correct horse battery staple"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json['token']}", "X-Sentinel-Org": tenant_id}
    assert client.post(f"/organizations/{tenant_id}/members", headers=admin_headers, json={"email": "owner@example.com", "role": "OWNER"}).status_code == 403


def test_auth_endpoints_reject_non_object_or_invalid_json_values(tmp_path):
    client = create_app(str(tmp_path)).test_client()
    assert client.post("/auth/register", json=[]).status_code == 400
    assert client.post("/auth/register", json={"email": None, "password": "valid password"}).status_code == 400
    assert client.post("/auth/login", json={"email": None, "password": None}).status_code == 401


def test_investigation_regression_contract_remains_compatible(tmp_path):
    result = InvestigationCoordinator(tmp_path).investigate(
        "compat-case-001",
        {"subject": "Verify password", "body": "Open https://example-login.com now."},
    )

    assert result.plan_name == "ai-investigator-v1"
    assert set(result.to_dict()) == {"plan_name", "results", "errors"}
    assert result.results["investigation"]["status"] == "completed"
