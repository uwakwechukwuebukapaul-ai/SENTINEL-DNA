"""Typed adapters over Sentinel DNA's existing canonical security boundaries."""
from typing import Protocol
from .exceptions import BillingError

class CanonicalRequestContextCapability(Protocol):
    def __call__(self): ...

class CanonicalAuthorizationCapability(Protocol):
    def require(self, context, tenant_id: str, operation: str) -> bool: ...

class CanonicalAuthorizationAdapter:
    def __init__(self, authorization_service):
        if authorization_service is None or not callable(getattr(authorization_service,"require_permission",None)): raise ValueError("canonical_authorization_required")
        self.service=authorization_service
    def require(self, context, tenant_id, operation):
        try: return self.service.require_permission(context,tenant_id,operation)
        except Exception as exc: raise BillingError("billing_authorization_denied") from exc
