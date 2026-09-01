"""Staging-only FAVP evidence custody and audit bootstrap helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _storage_path(value: str | os.PathLike[str] | None) -> Path:
    raw = str(value or os.getenv("SENTINEL_DNA_FAVP_EVIDENCE_DIR", "")).strip()
    if not raw:
        raise RuntimeError("SENTINEL_DNA_FAVP_EVIDENCE_DIR must be configured")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise RuntimeError("FAVP evidence directory must be absolute")
    if path.exists() and path.is_symlink():
        raise RuntimeError("FAVP evidence directory must not be a symlink")
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir() or not os.access(path, os.W_OK):
        raise RuntimeError("FAVP evidence directory is not writable")
    return path


def initialize_staging_artifacts(backend, evidence_dir: str | os.PathLike[str] | None = None) -> dict:
    """Write the non-secret storage declaration and one bootstrap audit event."""
    from services.audit.service import AuditService

    storage = _storage_path(evidence_dir)
    audit = AuditService(backend)
    audit.record(
        "FAVP_STAGING_SCHEMA_INITIALIZED",
        details={"migration_version": 9, "storage_schema": "favp-evidence-storage-v1"},
        actor_id="staging-migration",
        resource_type="favp_staging",
        resource_id="schema-v9",
        operation="staging_initialized",
        outcome="success",
    )
    marker = storage / ".favp-storage-manifest.json"
    marker.write_text(json.dumps({
        "schema": "favp-evidence-storage-v1",
        "storage_classification": "disposable_staging_favp_evidence",
        "synthetic_only": True,
        "production_access": "0",
    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {"evidence_dir": str(storage), "manifest": str(marker)}
