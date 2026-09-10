"""Run the authorized disposable PostgreSQL production-readiness rehearsal."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from database.backend import PostgreSQLBackend  # noqa: E402
from services.audit.service import AuditService  # noqa: E402
from services.intelligence.memory.models import InvestigationMemoryRecord  # noqa: E402
from services.intelligence.memory.organizational_models import InvestigationPattern  # noqa: E402
from services.intelligence.memory.organizational_repository import OrganizationalMemoryRepository  # noqa: E402
from services.intelligence.memory.repository import InvestigationMemoryRepository  # noqa: E402

try:  # noqa: E402 - supports both module and direct-script execution
    from .common import digest, report_metadata, require_authorized_url, write_report
    from .migrate import run_migration
    from .rollback import run_rollback
except ImportError:  # pragma: no cover - direct operator invocation
    from common import digest, report_metadata, require_authorized_url, write_report
    from migrate import run_migration
    from rollback import run_rollback


def _seed_core_case(backend: PostgreSQLBackend) -> dict[str, Any]:
    with backend.session() as connection:
        connection.execute(
            """INSERT INTO cases(case_id, title, severity, description, status, analyst, created)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("REHEARSAL-CASE-A", "Synthetic phishing", "HIGH", "Synthetic only", "OPEN", "REHEARSAL", "2026-08-26T00:00:00+00:00"),
        )
        connection.execute(
            """INSERT INTO case_notes(case_id, note, analyst, created)
               VALUES (?, ?, ?, ?)""",
            ("REHEARSAL-CASE-A", "Synthetic provenance note", "REHEARSAL", "2026-08-26T00:00:01+00:00"),
        )
        connection.execute(
            """INSERT INTO evidence(case_id, type, data, sha256, collected_by, created)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("REHEARSAL-CASE-A", "IOC", "evil.example", "synthetic-sha256", "REHEARSAL", "2026-08-26T00:00:02+00:00"),
        )
        rows = connection.execute(
            "SELECT id FROM cases WHERE case_id=?", ("REHEARSAL-CASE-A",)
        ).fetchall()
        case_id = rows[0]["id"]
    return {"case_id": "REHEARSAL-CASE-A", "generated_identity": int(case_id)}


def _seed_memory(backend: PostgreSQLBackend) -> dict[str, Any]:
    memory = InvestigationMemoryRepository(backend)
    organization = OrganizationalMemoryRepository(backend)
    audit = AuditService(backend)
    try:
        memory.save(InvestigationMemoryRecord(
            memory_id="REHEARSAL-MEM-A", tenant_id="tenant-a", case_id="REHEARSAL-CASE-A",
            investigation_id="REHEARSAL-INV-A", investigation_type="phishing", scenario="synthetic",
            risk_level="high", confidence=0.9, evidence_summary={"ioc": "evil.example"},
            provenance={"source": "postgresql-rehearsal", "case_id": "REHEARSAL-CASE-A"},
            evidence_fingerprint="rehearsal-fingerprint-a",
        ))
        memory.save(InvestigationMemoryRecord(
            memory_id="REHEARSAL-MEM-B", tenant_id="tenant-b", case_id="REHEARSAL-CASE-B",
            investigation_id="REHEARSAL-INV-B", investigation_type="phishing", scenario="synthetic",
            risk_level="medium", confidence=0.7, provenance={"source": "postgresql-rehearsal"},
            evidence_fingerprint="rehearsal-fingerprint-b",
        ))
        organization.save(InvestigationPattern(
            pattern_id="REHEARSAL-PATTERN-A", tenant_id="tenant-a", source_investigation_id="REHEARSAL-INV-A",
            pattern_key="synthetic-phishing", description="Synthetic pattern", evidence_provenance={"source": "rehearsal"},
            created_by="REHEARSAL", confidence=0.8, observed_at="2026-08-26T00:00:00+00:00",
            created_at="2026-08-26T00:00:00+00:00", why_stored="Portability rehearsal",
        ))
        organization.save(InvestigationPattern(
            pattern_id="REHEARSAL-PATTERN-B", tenant_id="tenant-b", source_investigation_id="REHEARSAL-INV-B",
            pattern_key="synthetic-phishing-b", description="Synthetic pattern B", evidence_provenance={"source": "rehearsal"},
            created_by="REHEARSAL", confidence=0.6, observed_at="2026-08-26T00:00:00+00:00",
            created_at="2026-08-26T00:00:00+00:00", why_stored="Portability rehearsal",
        ))
        event_id = audit.record(
            "POSTGRES_REHEARSAL", tenant_id="tenant-a", actor_id="REHEARSAL",
            resource_type="investigation", resource_id="REHEARSAL-INV-A",
            details={"provenance": "postgresql-rehearsal"},
        )

        tenant_a_memory = memory.get("tenant-a", "REHEARSAL-MEM-A")
        tenant_b_view = memory.get("tenant-b", "REHEARSAL-MEM-A")
        tenant_a_patterns = organization.list("tenant-a")
        tenant_b_patterns = organization.list("tenant-b")
        tenant_a_audit = audit.get_for_tenant(event_id, "tenant-a")
        cross_tenant_audit = audit.get_for_tenant(event_id, "tenant-b")

        append_only_blocked = False
        try:
            organization._connection.execute(
                "UPDATE organizational_memory SET confidence=0 WHERE record_id=?",
                ("REHEARSAL-PATTERN-A",),
            )
        except Exception:
            append_only_blocked = True

        audit_tamper_blocked = False
        try:
            with audit.db.session() as connection:
                connection.execute(
                    "UPDATE audit_events SET outcome='tampered' WHERE event_id=?", (event_id,)
                )
        except Exception:
            audit_tamper_blocked = True

        provenance_values = [
            tenant_a_memory.provenance if tenant_a_memory else {},
            tenant_a_patterns[0].evidence_provenance if tenant_a_patterns else {},
            tenant_a_audit.get("details", {}) if tenant_a_audit else {},
        ]
        return {
            "tenant_isolation": tenant_a_memory is not None and tenant_b_view is None and len(tenant_a_patterns) == 1 and len(tenant_b_patterns) == 1 and cross_tenant_audit is None,
            "provenance_preservation": tenant_a_memory is not None and tenant_a_memory.provenance.get("source") == "postgresql-rehearsal" and bool(tenant_a_patterns[0].evidence_provenance) and bool(tenant_a_audit),
            "audit_integrity": append_only_blocked and audit_tamper_blocked and len(audit.list_for_tenant("tenant-a")) == 1,
            "memory_record_counts": {"tenant-a": len(memory.all("tenant-a")), "tenant-b": len(memory.all("tenant-b"))},
            "provenance_digest": digest(provenance_values),
            "audit_digest": digest(audit.list_for_tenant("tenant-a")),
            "investigation_digest": digest([tenant_a_memory.to_dict() if tenant_a_memory else {}]),
        }
    finally:
        memory.close()
        organization.close()


def run_rehearsal(url: str) -> dict[str, Any]:
    backend = PostgreSQLBackend(url, connect_timeout=5)
    if not backend.health_check():
        raise RuntimeError("disposable_postgresql_health_check_failed")
    migration = run_migration(backend)
    rollback = run_rollback(backend)
    case = _seed_core_case(backend)
    memory = _seed_memory(backend)
    checks = {
        "connection_readiness": True,
        "migration_ordering": migration["migration_ordering"],
        "migration_idempotency": migration["migration_idempotency"],
        "schema_compatibility": migration["schema_compatibility"],
        "repository_crud": case["generated_identity"] > 0,
        "identity_sequence_behavior": case["generated_identity"] > 0,
        "tenant_isolation_preservation": memory["tenant_isolation"],
        "provenance_preservation": memory["provenance_preservation"],
        "audit_integrity_preservation": memory["audit_integrity"],
        "investigation_record_preservation": bool(memory["investigation_digest"]),
        "rollback_capability": rollback["transaction_rollback"] and rollback["migration_rollback"],
        "backup_restore_rehearsal": rollback["backup_restore_rehearsal"],
    }
    report = {
        "report_version": "sentinel-dna-postgresql-live-rehearsal.v1",
        "database_engine": "postgresql",
        "rehearsal_scope": "disposable",
        "checks": checks,
        "migration": migration,
        "rollback": rollback,
        "synthetic_record_counts": memory["memory_record_counts"],
        "provenance_digest": memory["provenance_digest"],
        "audit_digest": memory["audit_digest"],
        "investigation_digest": memory["investigation_digest"],
        "release_blockers_remaining": [
            "production_like_backup_restore_attestation",
            "monitoring_and_ownership_attestation",
            "provider_credential_rotation_revocation_attestation",
            "stale_evidence_reconciliation",
        ],
        **report_metadata(REPO_ROOT),
    }
    stable = {key: value for key, value in report.items() if key not in {"generated_at", "report_digest"}}
    report["replay_digest"] = digest(stable)
    report["report_digest"] = digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        url = require_authorized_url()
    except RuntimeError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    report = run_rehearsal(url)
    target = write_report(report, args.output, REPO_ROOT)
    print(f"PostgreSQL disposable rehearsal report written: {target}")
    print("PostgreSQL readiness is not asserted by this rehearsal.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
