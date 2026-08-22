"""Tenant-scoped notification routing preferences."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4


class OperationsNotificationRuleRepository:
    def __init__(self, db):
        self.db = db
        with db.session() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS operations_notification_rules (
                rule_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, policy_id TEXT NOT NULL,
                adapter TEXT NOT NULL, destination TEXT, enabled INTEGER NOT NULL,
                suppression_until TEXT, rule_json TEXT NOT NULL, created_at TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1, severity_threshold TEXT,
                cooldown_seconds INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
                escalation_behavior TEXT, route_key TEXT, secret_reference TEXT)""")
            columns = {row[1] for row in connection.execute("PRAGMA table_info(operations_notification_rules)").fetchall()}
            for name, definition in (("version", "INTEGER NOT NULL DEFAULT 1"), ("severity_threshold", "TEXT"), ("cooldown_seconds", "INTEGER NOT NULL DEFAULT 0"), ("max_attempts", "INTEGER NOT NULL DEFAULT 3"), ("escalation_behavior", "TEXT"), ("route_key", "TEXT"), ("secret_reference", "TEXT")):
                if name not in columns: connection.execute(f"ALTER TABLE operations_notification_rules ADD COLUMN {name} {definition}")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_operations_notification_rules ON operations_notification_rules(tenant_id, policy_id)")

    def append(self, *, tenant_id: str, policy_id: str, adapter: str = "deterministic-test", destination: str | None = None, enabled: bool = True, suppression_until: str | None = None, severity_threshold: str | None = None, cooldown_seconds: int = 0, max_attempts: int = 3, escalation_behavior: str | None = None, version: int | None = None, route_key: str | None = None, secret_reference: str | None = None):
        previous = self.history(tenant_id=tenant_id, policy_id=policy_id)
        event = {"rule_id": f"ONR-{uuid4().hex}", "route_key": str(route_key or f"route:{tenant_id}:{policy_id}"), "tenant_id": str(tenant_id), "policy_id": str(policy_id), "adapter": str(adapter), "destination": destination, "secret_reference": secret_reference, "enabled": bool(enabled), "suppression_until": suppression_until, "severity_threshold": severity_threshold, "cooldown_seconds": max(0, int(cooldown_seconds)), "max_attempts": max(1, min(10, int(max_attempts))), "escalation_behavior": escalation_behavior, "version": int(version or len(previous) + 1), "created_at": datetime.now(timezone.utc).isoformat()}
        with self.db.session() as connection:
            connection.execute("INSERT INTO operations_notification_rules(rule_id, tenant_id, policy_id, adapter, destination, enabled, suppression_until, rule_json, created_at, version, severity_threshold, cooldown_seconds, max_attempts, escalation_behavior, route_key, secret_reference) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (event["rule_id"], event["tenant_id"], event["policy_id"], event["adapter"], event["destination"], int(event["enabled"]), event["suppression_until"], json.dumps(event, sort_keys=True), event["created_at"], event["version"], event["severity_threshold"], event["cooldown_seconds"], event["max_attempts"], event["escalation_behavior"], event["route_key"], event["secret_reference"]))
        return event

    def list_for_tenant(self, *, tenant_id: str):
        with self.db.session() as connection:
            rows = connection.execute("SELECT route_key, rule_json FROM operations_notification_rules WHERE tenant_id=? ORDER BY created_at, rowid", (str(tenant_id),)).fetchall()
        latest = {}
        for row in rows: latest[row["route_key"] or json.loads(row["rule_json"])["rule_id"]] = json.loads(row["rule_json"])
        return list(latest.values())

    def history(self, *, tenant_id: str, policy_id: str | None = None):
        with self.db.session() as connection:
            if policy_id is None: rows = connection.execute("SELECT rule_json FROM operations_notification_rules WHERE tenant_id=? ORDER BY created_at, rowid", (str(tenant_id),)).fetchall()
            else: rows = connection.execute("SELECT rule_json FROM operations_notification_rules WHERE tenant_id=? AND policy_id=? ORDER BY created_at, rowid", (str(tenant_id), str(policy_id))).fetchall()
        return [json.loads(row["rule_json"]) for row in rows]
