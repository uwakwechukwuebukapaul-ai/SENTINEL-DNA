"""Authentication and authorization primitives for the SaaS boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
import os

from sentinel_dna.saas.database import SaaSDatabase
from sentinel_dna.saas.identity import IdentityStore, Membership, Role, ROLE_RANK, User, now_iso, validate_identifier


class AuthenticationError(PermissionError):
    pass


class AuthorizationError(PermissionError):
    pass


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user: User
    token: str | None = None


class PasswordHasher:
    # OWASP's current PBKDF2-HMAC-SHA256 guidance is 600,000 iterations.
    # Stored hashes keep their embedded iteration count for compatibility.
    iterations = 600_000

    @classmethod
    def hash_password(cls, password: str) -> str:
        if not isinstance(password, str):
            raise ValueError("password must be a string")
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        if len(password) > 1024:
            raise ValueError("password is too long")
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), cls.iterations)
        return f"pbkdf2_sha256${cls.iterations}${salt}${digest.hex()}"

    @classmethod
    def verify(cls, password: str, password_hash: str) -> bool:
        try:
            if not isinstance(password, str) or not isinstance(password_hash, str):
                return False
            algorithm, iterations, salt, digest = password_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
            return hmac.compare_digest(candidate, digest)
        except (ValueError, TypeError, AttributeError):
            return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, data_dir: str = "data", session_hours: int = 12, session_store=None) -> None:
        self.identity = IdentityStore(data_dir)
        self.database = SaaSDatabase(data_dir)
        if not 1 <= session_hours <= 168:
            raise ValueError("session_hours must be between 1 and 168")
        self.session_hours = session_hours
        if session_store is None and os.getenv("SENTINEL_DNA_REDIS_URL"):
            from sentinel_dna.platform.distributed import RedisSessionStore
            session_store = RedisSessionStore(os.environ["SENTINEL_DNA_REDIS_URL"])
        self.session_store = session_store

    def register(self, email: str, password: str, display_name: str, organization_name: str | None = None) -> dict:
        user = self.identity.create_user(email, display_name, PasswordHasher.hash_password(password))
        organization = None
        membership = None
        if organization_name:
            organization = self.identity.create_organization(organization_name)
            membership = self.identity.create_membership(user.user_id, organization.organization_id, Role.OWNER)
        return {"user": user, "organization": organization, "membership": membership}

    def login(self, email: str, password: str) -> AuthenticatedPrincipal:
        try:
            user = self.identity.get_user_by_email(email)
        except ValueError:
            raise AuthenticationError("invalid credentials") from None
        if user is None or not user.is_active:
            raise AuthenticationError("invalid credentials")
        if not PasswordHasher.verify(password, user.password_hash):
            raise AuthenticationError("invalid credentials")
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=self.session_hours)).isoformat()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (token_digest(token), user.user_id, expires_at, now_iso()),
            )
        if self.session_store:
            self.session_store.put(token_digest(token), user.user_id, self.session_hours * 3600)
        return AuthenticatedPrincipal(user=user, token=token)

    def authenticate_token(self, token: str | None) -> AuthenticatedPrincipal:
        if not isinstance(token, str) or not token or len(token) > 512:
            raise AuthenticationError("authentication required")
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT user_id FROM sessions WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > ?",
                (token_digest(token), now),
            ).fetchone()
        if row is None:
            raise AuthenticationError("authentication required")
        user = self.identity.get_user(row["user_id"])
        if user is None or not user.is_active:
            raise AuthenticationError("authentication required")
        if self.session_store and self.session_store.get(token_digest(token)) not in {None, user.user_id}:
            raise AuthenticationError("authentication required")
        return AuthenticatedPrincipal(user=user, token=token)

    def require_tenant_access(self, user_id: str, tenant_id: str) -> Membership:
        try:
            membership = self.identity.get_membership(user_id, tenant_id)
        except ValueError:
            raise AuthorizationError("tenant access denied") from None
        if membership is None:
            raise AuthorizationError("tenant access denied")
        return membership

    def require_role(self, user_id: str, tenant_id: str, *allowed_roles: Role | str) -> Membership:
        membership = self.require_tenant_access(user_id, tenant_id)
        try:
            allowed = {Role(role) for role in allowed_roles}
        except ValueError:
            raise AuthorizationError("role denied") from None
        if membership.role not in allowed:
            raise AuthorizationError("role denied")
        return membership

    def require_minimum_role(self, user_id: str, tenant_id: str, minimum_role: Role | str) -> Membership:
        membership = self.require_tenant_access(user_id, tenant_id)
        try:
            required_role = Role(minimum_role)
        except ValueError:
            raise AuthorizationError("role denied") from None
        if ROLE_RANK[membership.role] < ROLE_RANK[required_role]:
            raise AuthorizationError("role denied")
        return membership

    def revoke_token(self, token: str | None) -> None:
        if not isinstance(token, str) or not token:
            raise AuthenticationError("authentication required")
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
                (now_iso(), token_digest(token)),
            )
        if self.session_store:
            self.session_store.revoke(token_digest(token))


def require_authenticated_user(auth: AuthService, token: str | None) -> AuthenticatedPrincipal:
    return auth.authenticate_token(token)


def require_tenant_access(auth: AuthService, user_id: str, tenant_id: str) -> Membership:
    return auth.require_tenant_access(user_id, tenant_id)


def require_role(auth: AuthService, user_id: str, tenant_id: str, *roles: Role | str) -> Membership:
    return auth.require_role(user_id, tenant_id, *roles)
