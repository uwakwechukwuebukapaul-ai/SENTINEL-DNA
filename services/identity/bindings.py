"""Governed external-subject to canonical-actor bindings."""

from __future__ import annotations

from dataclasses import dataclass
from database.canonical_authority import CanonicalIdentityBindingRepository, CanonicalUnitOfWork
from database.connection import DatabaseConnection, database


class IdentityBindingError(ValueError): pass


@dataclass(frozen=True)
class IdentityBinding:
    binding_id: str
    provider: str
    external_subject: str
    actor_id: str
    status: str
    created_by: str
    revoked_at: str | None


def _binding(row):
    return IdentityBinding(row["binding_id"], row["provider"], row["external_subject"], row["actor_id"], row["status"], row["created_by"], row["revoked_at"]) if row else None


class IdentityBindingService:
    """Administrative binding owner; it never creates actors or membership."""

    VALID_STATUSES = {"active", "disabled", "revoked"}

    def __init__(self, db: DatabaseConnection = database, audit=None): self.db, self.audit = db, audit

    def bind(self, provider: str, external_subject: str, actor_id: str, created_by: str) -> IdentityBinding:
        values = [str(value).strip() for value in (provider, external_subject, actor_id, created_by)]
        if not all(values): raise IdentityBindingError("binding_fields_required")
        with CanonicalUnitOfWork(self.db) as unit:
            try: row = CanonicalIdentityBindingRepository(unit.conn).create(*values)
            except Exception as exc: raise IdentityBindingError("identity_binding_rejected") from exc
            if self.audit: self.audit.record("IDENTITY_BINDING_CREATED", details={"provider": values[0], "external_subject": values[1], "actor_id": values[2]}, connection=unit.conn)
            return _binding(row)

    def resolve(self, provider: str, external_subject: str) -> IdentityBinding:
        provider, external_subject = str(provider or "").strip(), str(external_subject or "").strip()
        if not provider or not external_subject: raise IdentityBindingError("binding_subject_required")
        with CanonicalUnitOfWork(self.db) as unit: binding = _binding(CanonicalIdentityBindingRepository(unit.conn).get(provider, external_subject))
        if not binding: raise IdentityBindingError("identity_binding_not_found")
        if binding.status != "active": raise IdentityBindingError("identity_binding_inactive")
        return binding

    def set_status(self, binding_id: str, status: str) -> IdentityBinding:
        if status not in self.VALID_STATUSES: raise IdentityBindingError("invalid_binding_status")
        with CanonicalUnitOfWork(self.db) as unit:
            row = CanonicalIdentityBindingRepository(unit.conn).set_status(binding_id, status)
            if row and self.audit: self.audit.record("IDENTITY_BINDING_STATUS_CHANGED", details={"binding_id": binding_id, "status": status}, connection=unit.conn)
        if not row: raise IdentityBindingError("identity_binding_not_found")
        return _binding(row)
