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

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id, "username": self.username, "email": self.email,
            "role": self.role, "created_at": self.created_at,
            "last_login": self.last_login, "is_active": self.is_active,
            "phone_number": self.masked_phone(), "phone_verified": bool(self.phone_verified_at),
        }

    def profile(self) -> dict[str, Any]:
        from .age import calculate_age, parse_date_of_birth
        payload = self.public()
        try:
            age = calculate_age(parse_date_of_birth(self.date_of_birth)) if self.date_of_birth else None
        except ValueError:
            age = None
        payload.update({
            "age": age,
            "age_verified": bool(self.date_of_birth) and age is not None,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
        })
        return payload

    def masked_phone(self) -> str | None:
        if not self.phone_number:
            return None
        return f"{self.phone_number[:4]}   {self.phone_number[-4:]}" if len(self.phone_number) > 8 else "***"
