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

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id, "username": self.username, "email": self.email,
            "role": self.role, "created_at": self.created_at,
            "last_login": self.last_login, "is_active": self.is_active,
        }
