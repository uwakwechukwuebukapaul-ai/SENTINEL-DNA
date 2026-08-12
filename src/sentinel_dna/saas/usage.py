"""Tenant-scoped usage metering for future commercial billing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from typing import Any
from uuid import uuid4

from sentinel_dna.saas.auth import AuthorizationError
from sentinel_dna.saas.database import SaaSDatabase
from sentinel_dna.saas.identity import validate_identifier


ALLOWED_USAGE_EVENTS = {
    "investigation_started",
    "investigation_completed",
    "evidence_processed",
    "ioc_enrichment",
    "report_generated",
    "api_request",
    "security_event",
    "billing_customer_created",
    "subscription_created",
    "subscription_updated",
    "subscription_canceled",
    "invoice_created",
    "invoice_paid",
    "invoice_payment_failed",
    "billing_reconciliation_required",
}
METRIC_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


@dataclass(frozen=True)
class UsageEvent:
    event_id: str
    tenant_id: str
    user_id: str | None
    event_type: str
    quantity: int
    resource_type: str | None
    resource_id: str | None
    metadata: dict[str, Any]
    created_at: str


class UsageMeter:
    def __init__(self, data_dir: str = "data") -> None:
        self.database = SaaSDatabase(data_dir)

    def record_event(
        self,
        tenant_id: str,
        event_type: str,
        quantity: int = 1,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UsageEvent:
        tenant_id = validate_identifier(tenant_id, "org")
        if not isinstance(event_type, str) or not METRIC_PATTERN.fullmatch(event_type):
            raise ValueError("invalid event_type")
        if event_type not in ALLOWED_USAGE_EVENTS:
            raise ValueError("unsupported event_type")
        if quantity < 0:
            raise ValueError("quantity must be non-negative")
        if quantity > 1_000_000:
            raise ValueError("quantity is too large")
        event = UsageEvent(
            event_id=f"use-{uuid4().hex}",
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            quantity=quantity,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO usage_events
                (event_id, tenant_id, user_id, event_type, quantity, resource_type, resource_id, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.tenant_id,
                    event.user_id,
                    event.event_type,
                    event.quantity,
                    event.resource_type,
                    event.resource_id,
                    json.dumps(event.metadata),
                    event.created_at,
                ),
            )
        return event

    def get_usage(
        self,
        tenant_id: str,
        metric: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> list[UsageEvent]:
        tenant_id = validate_identifier(tenant_id, "org")
        if metric is not None and not METRIC_PATTERN.fullmatch(metric):
            raise ValueError("invalid metric")
        query = "SELECT * FROM usage_events WHERE tenant_id = ?"
        parameters: list[Any] = [tenant_id]
        if metric:
            query += " AND event_type = ?"
            parameters.append(metric)
        if start:
            query += " AND created_at >= ?"
            parameters.append(start)
        if end:
            query += " AND created_at <= ?"
            parameters.append(end)
        query += " ORDER BY created_at"
        with self.database.connect() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [self._event_from_row(row) for row in rows]

    def aggregate_usage(
        self,
        tenant_id: str,
        metric: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, int]:
        totals: dict[str, int] = {}
        for event in self.get_usage(tenant_id, metric, start, end):
            totals[event.event_type] = totals.get(event.event_type, 0) + event.quantity
        return totals

    def assert_tenant(self, requested_tenant_id: str, authorized_tenant_id: str) -> None:
        if validate_identifier(requested_tenant_id, "org") != validate_identifier(authorized_tenant_id, "org"):
            raise AuthorizationError("usage access denied")

    def _event_from_row(self, row) -> UsageEvent:
        data = dict(row)
        data["metadata"] = json.loads(data["metadata"])
        return UsageEvent(**data)
