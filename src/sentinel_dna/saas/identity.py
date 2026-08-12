"""Identity and tenant membership storage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
import sqlite3
from typing import Any
from uuid import uuid4

from sentinel_dna.saas.database import SaaSDatabase


ID_PATTERN = re.compile(r"^(user|org|mbr)-[a-f0-9]{32}$")
# Canonical IDs are UUID based, but early beta tenants used bounded slugs such
# as ``org-test``.  Retain those safe legacy values at the SaaS boundary.
ORG_ID_PATTERN = re.compile(r"^org-(?:[a-f0-9]{32}|[a-z0-9][a-z0-9-]{0,62})$")
MAX_NAME_LENGTH = 160


class Role(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    SOC_MANAGER = "SOC_MANAGER"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


ROLE_RANK: dict[Role, int] = {
    Role.VIEWER: 10,
    Role.ANALYST: 20,
    Role.SOC_MANAGER: 30,
    Role.ADMIN: 40,
    Role.OWNER: 50,
}


@dataclass(frozen=True)
class User:
    user_id: str
    email: str
    display_name: str
    password_hash: str
    is_active: bool
    created_at: str


@dataclass(frozen=True)
class Organization:
    organization_id: str
    name: str
    created_at: str


@dataclass(frozen=True)
class Membership:
    membership_id: str
    user_id: str
    organization_id: str
    role: Role
    created_at: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_email(email: str) -> str:
    if not isinstance(email, str):
        raise ValueError("email must be a valid email address")
    normalized = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
        raise ValueError("email must be a valid email address")
    return normalized


def validate_identifier(identifier: str, expected_prefix: str | None = None) -> str:
    if not isinstance(identifier, str):
        raise ValueError("invalid identifier")
    normalized = identifier.strip()
    pattern = ORG_ID_PATTERN if expected_prefix == "org" else ID_PATTERN
    if not pattern.fullmatch(normalized):
        raise ValueError("invalid identifier")
    if expected_prefix and not normalized.startswith(f"{expected_prefix}-"):
        raise ValueError("invalid identifier")
    return normalized


class IdentityStore:
    def __init__(self, data_dir: str = "data") -> None:
        self.database = SaaSDatabase(data_dir)

    def create_user(self, email: str, display_name: str, password_hash: str, is_active: bool = True) -> User:
        clean_display_name = str(display_name or "").strip()
        if len(clean_display_name) > MAX_NAME_LENGTH:
            raise ValueError("display name is too long")
        user = User(
            user_id=f"user-{uuid4().hex}",
            email=normalize_email(email),
            display_name=clean_display_name or normalize_email(email),
            password_hash=password_hash,
            is_active=is_active,
            created_at=now_iso(),
        )
        try:
            with self.database.connect() as connection:
                connection.execute(
                    "INSERT INTO users (user_id, email, display_name, password_hash, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (user.user_id, user.email, user.display_name, user.password_hash, int(user.is_active), user.created_at),
                )
        except sqlite3.IntegrityError:
            raise ValueError("user already exists") from None
        return user

    def get_user_by_email(self, email: str) -> User | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE email = ?", (normalize_email(email),)).fetchone()
        return self._user_from_row(row) if row else None

    def get_user(self, user_id: str) -> User | None:
        user_id = validate_identifier(user_id, "user")
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return self._user_from_row(row) if row else None

    def create_organization(self, name: str) -> Organization:
        clean_name = str(name or "").strip()
        if len(clean_name) > MAX_NAME_LENGTH:
            raise ValueError("organization name is too long")
        organization = Organization(
            organization_id=f"org-{uuid4().hex}",
            name=clean_name,
            created_at=now_iso(),
        )
        if not organization.name:
            raise ValueError("organization name is required")
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO organizations (organization_id, name, created_at) VALUES (?, ?, ?)",
                (organization.organization_id, organization.name, organization.created_at),
            )
        return organization

    def get_organization(self, organization_id: str) -> Organization | None:
        organization_id = validate_identifier(organization_id, "org")
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM organizations WHERE organization_id = ?",
                (organization_id,),
            ).fetchone()
        return Organization(**dict(row)) if row else None

    def create_membership(self, user_id: str, organization_id: str, role: Role | str) -> Membership:
        user_id = validate_identifier(user_id, "user")
        organization_id = validate_identifier(organization_id, "org")
        membership = Membership(
            membership_id=f"mbr-{uuid4().hex}",
            user_id=user_id,
            organization_id=organization_id,
            role=Role(role),
            created_at=now_iso(),
        )
        try:
            with self.database.connect() as connection:
                connection.execute(
                    "INSERT INTO memberships (membership_id, user_id, organization_id, role, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        membership.membership_id,
                        membership.user_id,
                        membership.organization_id,
                        membership.role.value,
                        membership.created_at,
                    ),
                )
        except sqlite3.IntegrityError:
            raise ValueError("membership already exists or references invalid user/organization") from None
        return membership

    def get_membership(self, user_id: str, organization_id: str) -> Membership | None:
        user_id = validate_identifier(user_id, "user")
        organization_id = validate_identifier(organization_id, "org")
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM memberships WHERE user_id = ? AND organization_id = ?",
                (user_id, organization_id),
            ).fetchone()
        return self._membership_from_row(row) if row else None

    def list_user_organizations(self, user_id: str) -> list[dict[str, Any]]:
        user_id = validate_identifier(user_id, "user")
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT o.organization_id, o.name, o.created_at, m.role
                FROM organizations o
                JOIN memberships m ON m.organization_id = o.organization_id
                WHERE m.user_id = ?
                ORDER BY o.name
                """,
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_members(self, organization_id: str) -> list[dict[str, Any]]:
        organization_id = validate_identifier(organization_id, "org")
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT u.user_id, u.email, u.display_name, u.is_active, m.role, m.created_at
                FROM users u
                JOIN memberships m ON m.user_id = u.user_id
                WHERE m.organization_id = ?
                ORDER BY u.email
                """,
                (organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _user_from_row(self, row) -> User:
        data = dict(row)
        data["is_active"] = bool(data["is_active"])
        return User(**data)

    def _membership_from_row(self, row) -> Membership:
        data = dict(row)
        data["role"] = Role(data["role"])
        return Membership(**data)
