from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import uuid4
from .models import APIRequestContext

class AuthenticationProvider(ABC):
    @abstractmethod
    def authenticate(self, credentials=None, *, source="api") -> APIRequestContext: ...

class DevelopmentAuthenticationProvider(AuthenticationProvider):
    """Explicit, non-credential fallback for local/test wiring only."""
    def __init__(self, enabled: bool = False, default_tenant: str | None = None):
        self.enabled, self.default_tenant = enabled, default_tenant
    def authenticate(self, credentials=None, *, source="development") -> APIRequestContext:
        if not self.enabled: raise PermissionError("authentication_required")
        value = credentials or {}
        return APIRequestContext(str(value.get("request_id") or uuid4()), value.get("tenant_id") or self.default_tenant, value.get("user_id"), value.get("role", "viewer"), source=source, permissions=list(value.get("permissions", [])))

class TokenAuthenticationProvider(AuthenticationProvider):
    """Future JWT/OAuth seam; token validation is deliberately delegated."""
    def __init__(self, validator): self.validator = validator
    def authenticate(self, credentials=None, *, source="api"):
        if not credentials or not callable(self.validator): raise PermissionError("authentication_required")
        claims = self.validator(credentials)
        if not claims: raise PermissionError("authentication_failed")
        return APIRequestContext(str(claims.get("request_id") or uuid4()), claims.get("tenant_id"), claims.get("user_id"), claims.get("role", "viewer"), source=source, permissions=list(claims.get("permissions", [])))
