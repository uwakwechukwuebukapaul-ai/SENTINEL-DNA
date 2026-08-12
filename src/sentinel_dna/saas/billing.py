"""Provider-neutral commercial billing and entitlement boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import re
from typing import Any, Protocol
from uuid import uuid4

from sentinel_dna.saas.auth import AuthorizationError
from sentinel_dna.saas.database import SaaSDatabase
from sentinel_dna.saas.identity import validate_identifier
from sentinel_dna.saas.usage import UsageMeter


class BillingConfigurationError(RuntimeError):
    pass


class EntitlementError(PermissionError):
    pass


PLAN_ID_PATTERN = re.compile(r"^plan-[a-z0-9][a-z0-9-]{1,62}$")
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
ACTIVE_SUBSCRIPTION_STATUSES = {"trialing", "active"}
BILLING_AUDIT_EVENTS = {
    "billing_customer_created",
    "subscription_created",
    "subscription_updated",
    "subscription_canceled",
    "invoice_created",
    "invoice_paid",
    "invoice_payment_failed",
    "billing_reconciliation_required",
}


@dataclass(frozen=True)
class BillingPlan:
    plan_id: str
    name: str
    status: str
    billing_interval: str
    price_cents: int
    currency: str
    entitlements: dict[str, int]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class BillingCustomer:
    customer_id: str
    tenant_id: str
    provider: str
    provider_customer_id: str | None
    billing_email: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Subscription:
    subscription_id: str
    tenant_id: str
    plan_id: str
    status: str
    provider: str
    provider_subscription_id: str | None
    current_period_start: str
    current_period_end: str
    cancel_at_period_end: bool
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    tenant_id: str
    subscription_id: str | None
    status: str
    amount_due_cents: int
    currency: str
    provider: str
    provider_invoice_id: str | None
    idempotency_key: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


class BillingProvider(Protocol):
    provider_name: str

    def create_checkout_session(self, tenant_id: str, plan: BillingPlan, idempotency_key: str) -> dict[str, Any]:
        ...

    def create_customer(self, tenant_id: str, billing_email: str, idempotency_key: str) -> dict[str, Any]:
        ...

    def retrieve_subscription(self, provider_subscription_id: str) -> dict[str, Any]:
        ...

    def cancel_subscription(self, provider_subscription_id: str, idempotency_key: str) -> dict[str, Any]:
        ...

    def retrieve_invoices(self, provider_customer_id: str) -> list[dict[str, Any]]:
        ...

    def verify_webhook_signature(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        ...


class NotConfiguredBillingProvider:
    provider_name = "not_configured"

    def create_checkout_session(self, tenant_id: str, plan: BillingPlan, idempotency_key: str) -> dict[str, Any]:
        raise BillingConfigurationError("billing provider is not configured")

    def create_customer(self, tenant_id: str, billing_email: str, idempotency_key: str) -> dict[str, Any]:
        raise BillingConfigurationError("billing provider is not configured")

    def retrieve_subscription(self, provider_subscription_id: str) -> dict[str, Any]:
        raise BillingConfigurationError("billing provider is not configured")

    def cancel_subscription(self, provider_subscription_id: str, idempotency_key: str) -> dict[str, Any]:
        raise BillingConfigurationError("billing provider is not configured")

    def retrieve_invoices(self, provider_customer_id: str) -> list[dict[str, Any]]:
        raise BillingConfigurationError("billing provider is not configured")

    def verify_webhook_signature(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        raise BillingConfigurationError("billing provider is not configured")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_plan_id(plan_id: str) -> str:
    if not isinstance(plan_id, str) or not PLAN_ID_PATTERN.fullmatch(plan_id):
        raise ValueError("invalid plan_id")
    return plan_id


def validate_idempotency_key(idempotency_key: str) -> str:
    if not isinstance(idempotency_key, str) or not IDEMPOTENCY_PATTERN.fullmatch(idempotency_key):
        raise ValueError("invalid idempotency_key")
    return idempotency_key


class BillingService:
    def __init__(self, data_dir: str = "data", provider: BillingProvider | None = None) -> None:
        self.database = SaaSDatabase(data_dir)
        self.usage = UsageMeter(data_dir)
        self.provider = provider or NotConfiguredBillingProvider()
        self.ensure_default_plans()

    def ensure_default_plans(self) -> None:
        defaults = [
            ("plan-free", "Free", 0, {"investigation_started": 3, "report_generated": 3, "retention_days": 30}),
            ("plan-team", "Team", 4900, {"investigation_started": 250, "report_generated": 250, "retention_days": 365}),
            ("plan-enterprise", "Enterprise", 0, {"investigation_started": 10000, "report_generated": 10000, "retention_days": 3650}),
        ]
        for plan_id, name, price_cents, entitlements in defaults:
            if self.get_plan(plan_id) is None:
                self.create_plan(plan_id, name, price_cents, entitlements)

    def create_plan(self, plan_id: str, name: str, price_cents: int, entitlements: dict[str, int]) -> BillingPlan:
        plan_id = validate_plan_id(plan_id)
        if price_cents < 0:
            raise ValueError("price_cents must be non-negative")
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("name is required")
        for key, value in entitlements.items():
            if not isinstance(key, str) or not isinstance(value, int) or value < 0:
                raise ValueError("invalid entitlement")
        timestamp = now_iso()
        plan = BillingPlan(plan_id, clean_name, "active", "month", price_cents, "USD", entitlements, timestamp, timestamp)
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO billing_plans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (plan.plan_id, plan.name, plan.status, plan.billing_interval, plan.price_cents, plan.currency, json.dumps(plan.entitlements), plan.created_at, plan.updated_at),
            )
        return plan

    def list_plans(self) -> list[BillingPlan]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM billing_plans WHERE status = ? ORDER BY price_cents, plan_id", ("active",)).fetchall()
        return [self._plan_from_row(row) for row in rows]

    def get_plan(self, plan_id: str) -> BillingPlan | None:
        plan_id = validate_plan_id(plan_id)
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM billing_plans WHERE plan_id = ?", (plan_id,)).fetchone()
        return self._plan_from_row(row) if row else None

    def create_customer(self, tenant_id: str, billing_email: str, idempotency_key: str, metadata: dict[str, Any] | None = None) -> BillingCustomer:
        tenant_id = validate_identifier(tenant_id, "org")
        validate_idempotency_key(idempotency_key)
        clean_email = str(billing_email or "").strip().lower()
        if "@" not in clean_email or len(clean_email) > 254:
            raise ValueError("invalid billing_email")
        existing = self.get_customer(tenant_id)
        if existing:
            return existing
        timestamp = now_iso()
        provider_customer_id = None
        if self.provider.provider_name != "not_configured":
            provider_customer_id = self.provider.create_customer(tenant_id, clean_email, idempotency_key).get("id")
        customer = BillingCustomer(f"bcus-{uuid4().hex}", tenant_id, self.provider.provider_name, provider_customer_id, clean_email, metadata or {}, timestamp, timestamp)
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO billing_customers VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (customer.customer_id, customer.tenant_id, customer.provider, customer.provider_customer_id, customer.billing_email, json.dumps(customer.metadata), customer.created_at, customer.updated_at),
            )
        self._audit(tenant_id, "billing_customer_created", {"customer_id": customer.customer_id})
        return customer

    def get_customer(self, tenant_id: str) -> BillingCustomer | None:
        tenant_id = validate_identifier(tenant_id, "org")
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM billing_customers WHERE tenant_id = ?", (tenant_id,)).fetchone()
        return self._customer_from_row(row) if row else None

    def create_subscription(self, tenant_id: str, plan_id: str, idempotency_key: str, metadata: dict[str, Any] | None = None) -> Subscription:
        tenant_id = validate_identifier(tenant_id, "org")
        plan = self.get_plan(plan_id)
        if plan is None or plan.status != "active":
            raise ValueError("plan is not available")
        if self.find_subscription_event(tenant_id, idempotency_key):
            current = self.get_subscription(tenant_id)
            if current is None:
                raise ValueError("idempotency conflict")
            return current
        existing = self.get_subscription(tenant_id)
        if existing and existing.status in ACTIVE_SUBSCRIPTION_STATUSES:
            raise ValueError("active subscription already exists")
        timestamp = now_iso()
        period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        subscription = Subscription(f"sub-{uuid4().hex}", tenant_id, plan.plan_id, "trialing", self.provider.provider_name, None, timestamp, period_end, False, metadata or {}, timestamp, timestamp)
        with self.database.connect() as connection:
            connection.execute("DELETE FROM billing_subscriptions WHERE tenant_id = ?", (tenant_id,))
            connection.execute(
                "INSERT INTO billing_subscriptions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (subscription.subscription_id, subscription.tenant_id, subscription.plan_id, subscription.status, subscription.provider, subscription.provider_subscription_id, subscription.current_period_start, subscription.current_period_end, int(subscription.cancel_at_period_end), json.dumps(subscription.metadata), subscription.created_at, subscription.updated_at),
            )
            connection.execute(
                "INSERT INTO subscription_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"bevt-{uuid4().hex}", tenant_id, subscription.subscription_id, "subscription_created", validate_idempotency_key(idempotency_key), json.dumps({}), timestamp),
            )
        self._audit(tenant_id, "subscription_created", {"subscription_id": subscription.subscription_id, "plan_id": plan.plan_id})
        return subscription

    def cancel_subscription(self, tenant_id: str, idempotency_key: str) -> Subscription:
        tenant_id = validate_identifier(tenant_id, "org")
        validate_idempotency_key(idempotency_key)
        subscription = self.get_subscription(tenant_id)
        if subscription is None:
            raise ValueError("subscription not found")
        if self.find_subscription_event(tenant_id, idempotency_key):
            return subscription
        if subscription.provider_subscription_id and self.provider.provider_name != "not_configured":
            self.provider.cancel_subscription(subscription.provider_subscription_id, idempotency_key)
        timestamp = now_iso()
        with self.database.connect() as connection:
            connection.execute("UPDATE billing_subscriptions SET status = ?, cancel_at_period_end = ?, updated_at = ? WHERE tenant_id = ?", ("canceled", 1, timestamp, tenant_id))
            connection.execute("INSERT INTO subscription_events VALUES (?, ?, ?, ?, ?, ?, ?)", (f"bevt-{uuid4().hex}", tenant_id, subscription.subscription_id, "subscription_canceled", idempotency_key, json.dumps({}), timestamp))
        self._audit(tenant_id, "subscription_canceled", {"subscription_id": subscription.subscription_id})
        return self.get_subscription(tenant_id)

    def apply_provider_subscription(
        self,
        tenant_id: str,
        plan_id: str,
        status: str,
        provider_subscription_id: str,
        idempotency_key: str,
        period_start: str | None = None,
        period_end: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Subscription:
        tenant_id = validate_identifier(tenant_id, "org")
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError("plan is not available")
        if self.find_subscription_event(tenant_id, idempotency_key):
            current = self.get_subscription(tenant_id)
            if current is None:
                raise ValueError("idempotency conflict")
            return current
        timestamp = now_iso()
        subscription = Subscription(
            f"sub-{uuid4().hex}",
            tenant_id,
            plan.plan_id,
            status,
            self.provider.provider_name,
            provider_subscription_id,
            period_start or timestamp,
            period_end or (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            status == "canceled",
            metadata or {},
            timestamp,
            timestamp,
        )
        with self.database.connect() as connection:
            connection.execute("DELETE FROM billing_subscriptions WHERE tenant_id = ?", (tenant_id,))
            connection.execute(
                "INSERT INTO billing_subscriptions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (subscription.subscription_id, subscription.tenant_id, subscription.plan_id, subscription.status, subscription.provider, subscription.provider_subscription_id, subscription.current_period_start, subscription.current_period_end, int(subscription.cancel_at_period_end), json.dumps(subscription.metadata), subscription.created_at, subscription.updated_at),
            )
            connection.execute("INSERT INTO subscription_events VALUES (?, ?, ?, ?, ?, ?, ?)", (f"bevt-{uuid4().hex}", tenant_id, subscription.subscription_id, "subscription_updated", validate_idempotency_key(idempotency_key), json.dumps(metadata or {}), timestamp))
        self._audit(tenant_id, "subscription_updated", {"subscription_id": subscription.subscription_id, "provider_subscription_id": provider_subscription_id, "status": status})
        return subscription

    def get_subscription(self, tenant_id: str) -> Subscription | None:
        tenant_id = validate_identifier(tenant_id, "org")
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM billing_subscriptions WHERE tenant_id = ?", (tenant_id,)).fetchone()
        return self._subscription_from_row(row) if row else None

    def create_invoice(self, tenant_id: str, idempotency_key: str) -> Invoice:
        tenant_id = validate_identifier(tenant_id, "org")
        idempotency_key = validate_idempotency_key(idempotency_key)
        existing = self.get_invoice_by_idempotency(tenant_id, idempotency_key)
        if existing:
            return existing
        subscription = self.get_subscription(tenant_id)
        if subscription is None:
            raise ValueError("subscription not found")
        plan = self.get_plan(subscription.plan_id)
        timestamp = now_iso()
        invoice = Invoice(f"inv-{uuid4().hex}", tenant_id, subscription.subscription_id, "open", plan.price_cents, plan.currency, self.provider.provider_name, None, idempotency_key, {}, timestamp, timestamp)
        with self.database.connect() as connection:
            connection.execute("INSERT INTO invoices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (invoice.invoice_id, invoice.tenant_id, invoice.subscription_id, invoice.status, invoice.amount_due_cents, invoice.currency, invoice.provider, invoice.provider_invoice_id, invoice.idempotency_key, json.dumps(invoice.metadata), invoice.created_at, invoice.updated_at))
        self._audit(tenant_id, "invoice_created", {"invoice_id": invoice.invoice_id})
        return invoice

    def apply_provider_invoice(self, tenant_id: str, provider_invoice: dict[str, Any], idempotency_key: str) -> Invoice:
        tenant_id = validate_identifier(tenant_id, "org")
        existing = self.get_invoice_by_idempotency(tenant_id, idempotency_key)
        if existing:
            return existing
        subscription = self.get_subscription(tenant_id)
        status = str(provider_invoice.get("status") or "open")
        amount_due = int(provider_invoice.get("amount_due") or provider_invoice.get("amount_paid") or 0)
        currency = str(provider_invoice.get("currency") or "usd").upper()
        timestamp = now_iso()
        invoice = Invoice(f"inv-{uuid4().hex}", tenant_id, subscription.subscription_id if subscription else None, status, amount_due, currency, self.provider.provider_name, provider_invoice.get("id"), validate_idempotency_key(idempotency_key), provider_invoice, timestamp, timestamp)
        with self.database.connect() as connection:
            connection.execute("INSERT INTO invoices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (invoice.invoice_id, invoice.tenant_id, invoice.subscription_id, invoice.status, invoice.amount_due_cents, invoice.currency, invoice.provider, invoice.provider_invoice_id, invoice.idempotency_key, json.dumps(invoice.metadata), invoice.created_at, invoice.updated_at))
        self._audit(tenant_id, "invoice_paid" if status == "paid" else "invoice_payment_failed", {"invoice_id": invoice.invoice_id, "provider_invoice_id": invoice.provider_invoice_id, "status": status})
        return invoice

    def list_invoices(self, tenant_id: str) -> list[Invoice]:
        tenant_id = validate_identifier(tenant_id, "org")
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM invoices WHERE tenant_id = ? ORDER BY created_at DESC", (tenant_id,)).fetchall()
        return [self._invoice_from_row(row) for row in rows]

    def start_checkout(self, tenant_id: str, plan_id: str, idempotency_key: str) -> dict[str, Any]:
        tenant_id = validate_identifier(tenant_id, "org")
        idempotency_key = validate_idempotency_key(idempotency_key)
        existing = self.find_subscription_event(tenant_id, idempotency_key)
        if existing:
            metadata = json.loads(existing["metadata"])
            session = metadata.get("checkout_session")
            if not isinstance(session, dict):
                raise ValueError("idempotency conflict")
            return session
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError("plan is not available")
        session = self.provider.create_checkout_session(tenant_id, plan, idempotency_key)
        timestamp = now_iso()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO subscription_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    f"bevt-{uuid4().hex}",
                    tenant_id,
                    None,
                    "checkout_created",
                    idempotency_key,
                    json.dumps({"checkout_session": session}),
                    timestamp,
                ),
            )
        return session

    def record_provider_event(self, provider_event_id: str, event_type: str, tenant_id: str | None, payload: dict[str, Any]) -> bool:
        if not isinstance(provider_event_id, str) or not provider_event_id:
            raise ValueError("invalid provider event")
        timestamp = now_iso()
        try:
            with self.database.connect() as connection:
                connection.execute(
                    "INSERT INTO billing_provider_events VALUES (?, ?, ?, ?, ?, ?)",
                    (provider_event_id, self.provider.provider_name, event_type, tenant_id, timestamp, json.dumps(payload)),
                )
            return True
        except Exception:
            return False

    def audit_reconciliation_required(self, tenant_id: str, reason: str, metadata: dict[str, Any] | None = None) -> None:
        self._audit(validate_identifier(tenant_id, "org"), "billing_reconciliation_required", {"reason": reason, **(metadata or {})})

    def enforce_entitlement(self, tenant_id: str, metric: str, requested_quantity: int = 1) -> None:
        tenant_id = validate_identifier(tenant_id, "org")
        subscription = self.get_subscription(tenant_id)
        if subscription is None or subscription.status not in ACTIVE_SUBSCRIPTION_STATUSES:
            raise EntitlementError("active subscription required")
        plan = self.get_plan(subscription.plan_id)
        limit = plan.entitlements.get(metric)
        if limit is None:
            raise EntitlementError("entitlement unavailable")
        used = self.usage.aggregate_usage(tenant_id, metric, subscription.current_period_start, subscription.current_period_end).get(metric, 0)
        if used + requested_quantity > limit:
            raise EntitlementError("entitlement limit exceeded")

    def find_subscription_event(self, tenant_id: str, idempotency_key: str):
        tenant_id = validate_identifier(tenant_id, "org")
        idempotency_key = validate_idempotency_key(idempotency_key)
        with self.database.connect() as connection:
            return connection.execute("SELECT * FROM subscription_events WHERE tenant_id = ? AND idempotency_key = ?", (tenant_id, idempotency_key)).fetchone()

    def get_invoice_by_idempotency(self, tenant_id: str, idempotency_key: str) -> Invoice | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM invoices WHERE tenant_id = ? AND idempotency_key = ?", (validate_identifier(tenant_id, "org"), validate_idempotency_key(idempotency_key))).fetchone()
        return self._invoice_from_row(row) if row else None

    def _audit(self, tenant_id: str, event_type: str, metadata: dict[str, Any]) -> None:
        if event_type not in BILLING_AUDIT_EVENTS:
            raise ValueError("unsupported billing audit event")
        self.usage.record_event(tenant_id, event_type, metadata=metadata)

    def _plan_from_row(self, row) -> BillingPlan:
        data = dict(row); data["entitlements"] = json.loads(data["entitlements"]); return BillingPlan(**data)

    def _customer_from_row(self, row) -> BillingCustomer:
        data = dict(row); data["metadata"] = json.loads(data["metadata"]); return BillingCustomer(**data)

    def _subscription_from_row(self, row) -> Subscription:
        data = dict(row); data["metadata"] = json.loads(data["metadata"]); data["cancel_at_period_end"] = bool(data["cancel_at_period_end"]); return Subscription(**data)

    def _invoice_from_row(self, row) -> Invoice:
        data = dict(row); data["metadata"] = json.loads(data["metadata"]); return Invoice(**data)
