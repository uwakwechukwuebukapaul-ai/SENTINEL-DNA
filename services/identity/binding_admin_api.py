"""Thin, canonical-context-only administrative API facade.

HTTP exposure is intentionally deferred until Flask can obtain a trusted
canonical request context. This facade is the safe application boundary for
that future adapter.
"""

from __future__ import annotations

from .binding_administration import IdentityBindingAdministrationService
from .bindings import IdentityBindingError


class BindingAdminAPIError(ValueError): pass


class IdentityBindingAdminAPI:
    ALLOWED_CREATE = {"provider", "external_subject", "actor_id", "created_by"}

    def __init__(self, administration: IdentityBindingAdministrationService):
        if administration is None: raise ValueError("binding_administration_required")
        self.administration = administration

    def create(self, context, payload):
        data = self._payload(payload, self.ALLOWED_CREATE)
        return self.administration.create_binding(context, data["provider"], data["external_subject"], data["actor_id"], data["created_by"])

    def disable(self, context, binding_id): return self.administration.disable_binding(context, self._id(binding_id))
    def reactivate(self, context, binding_id): return self.administration.reactivate_binding(context, self._id(binding_id))
    def revoke(self, context, binding_id): return self.administration.revoke_binding(context, self._id(binding_id))

    @staticmethod
    def _payload(payload, allowed):
        if not isinstance(payload, dict): raise BindingAdminAPIError("malformed_request")
        unexpected = set(payload) - allowed
        if unexpected: raise BindingAdminAPIError("unexpected_security_fields")
        values = {key: str(payload.get(key, "")).strip() for key in allowed}
        if not all(values.values()): raise BindingAdminAPIError("required_field_missing")
        if any(len(value) > 256 for value in values.values()): raise BindingAdminAPIError("field_too_large")
        return values

    @staticmethod
    def _id(binding_id):
        value = str(binding_id or "").strip()
        if not value or len(value) > 256: raise BindingAdminAPIError("invalid_binding_id")
        return value

