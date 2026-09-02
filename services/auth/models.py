"""Authentication persistence models."""

from dataclasses import dataclass
from typing import Any


@dataclass
class User:
    id: int | None
    username: str
    email: str
    password_hash: str
    role: str
    created_at: str
    last_login: str | None
    is_active: bool
    phone_number: str | None = None
    phone_verified_at: str | None = None
    tenant_id: str | None = None
    actor_id: str | None = None
    date_of_birth: str | None = None
    email_verified_at: str | None = None
    session_version: int = 0
    expires_at: str | None = None
    revocation_status: str = "active"
    audit_correlation_id: str | None = None
    onboarding_state: str = "AUTHENTICATED"

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id, "username": self.username, "email": self.email,
            "role": self.role, "created_at": self.created_at,
            "last_login": self.last_login, "is_active": self.is_active,
            "phone_verified": bool(self.phone_verified_at),
            "email_verified": bool(self.email_verified_at),
            "onboarding_state": self.onboarding_state,
            "age": self.age(), "age_verified": self.age() is not None,
            "phone": self._masked_phone(),
        }

    def age(self):
        if not self.date_of_birth: return None
        from .age import calculate_age
        return calculate_age(self.date_of_birth)

    def _masked_phone(self):
        if not self.phone_number: return None
        return self.phone_number[:4] + "…" + self.phone_number[-4:]
