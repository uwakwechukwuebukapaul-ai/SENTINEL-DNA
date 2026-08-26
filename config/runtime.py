"""Environment-aware deployment configuration."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
import secrets

from database.backend import DatabaseConfigurationError, DatabaseSettings


_VALID_ENVIRONMENTS = {"development", "testing", "test", "staging", "production"}
_PRODUCTION_PLACEHOLDERS = {
    "development-only-secret",
    "development-only-change-me",
    "change-me-before-production",
}

@dataclass(frozen=True)
class RuntimeConfig:
    environment: str
    database_path: str
    secret_key: str
    secure_cookies: bool
    debug: bool
    database_url: str = ""

    @classmethod
    def from_environment(cls) -> "RuntimeConfig":
        environment = os.getenv("SENTINEL_DNA_ENV", os.getenv("FLASK_ENV", "development")).lower()
        debug = environment == "development" or (
            os.getenv("FLASK_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
        )
        configured_secret = os.getenv("SENTINEL_DNA_SECRET_KEY")
        secret_key = configured_secret if configured_secret is not None else (
            "" if environment == "production" else secrets.token_urlsafe(48)
        )
        return cls(
            environment,
            os.getenv("SENTINEL_DNA_DB_PATH", str(Path("soc.db"))),
            secret_key,
            os.getenv("SENTINEL_DNA_SECURE_COOKIES", "0") == "1",
            debug,
            os.getenv("DATABASE_URL", "").strip(),
        )

    def validate(self) -> None:
        if self.environment not in _VALID_ENVIRONMENTS:
            raise RuntimeError("SENTINEL_DNA_ENV must be a supported environment")

        if self.environment != "production":
            return

        if (
            len(self.secret_key.strip()) < 32
            or self.secret_key.strip().lower() in _PRODUCTION_PLACEHOLDERS
            or "change-me" in self.secret_key.strip().lower()
            or "replace-with" in self.secret_key.strip().lower()
        ):
            raise RuntimeError("SENTINEL_DNA_SECRET_KEY must be configured for production")

        if not self.secure_cookies:
            raise RuntimeError("SENTINEL_DNA_SECURE_COOKIES must be enabled for production")

        if self.debug:
            raise RuntimeError("SENTINEL_DNA_DEBUG must be disabled for production")

        if self.database_url.strip():
            try:
                DatabaseSettings.from_environment(
                    database_url=self.database_url,
                    require_postgresql=True,
                )
            except DatabaseConfigurationError as exc:
                raise RuntimeError(str(exc)) from exc
            return

        # Retain the pre-existing SQLite path contract for compatibility with
        # local/staging tooling. The process-level backend factory is the
        # production fail-closed boundary and rejects this configuration when
        # production starts without DATABASE_URL.
        database_path = os.getenv("SENTINEL_DNA_DB_PATH")
        if not database_path:
            raise RuntimeError("SENTINEL_DNA_DB_PATH must be configured for production")

        parent = Path(database_path).expanduser().resolve().parent
        if not parent.is_dir() or not os.access(parent, os.W_OK):
            raise RuntimeError("SENTINEL_DNA_DB_PATH must point to a usable database location")
