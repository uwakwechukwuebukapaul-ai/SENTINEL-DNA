"""Environment-aware deployment configuration."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path


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

    @classmethod
    def from_environment(cls) -> "RuntimeConfig":
        environment = os.getenv("SENTINEL_DNA_ENV", os.getenv("FLASK_ENV", "development")).lower()
        debug = environment == "development" or (
            os.getenv("FLASK_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
        )
        return cls(
            environment,
            os.getenv("SENTINEL_DNA_DB_PATH", str(Path("soc.db"))),
            os.getenv("SENTINEL_DNA_SECRET_KEY", "development-only-secret"),
            os.getenv("SENTINEL_DNA_SECURE_COOKIES", "0") == "1",
            debug,
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

        database_path = os.getenv("SENTINEL_DNA_DB_PATH")
        if not database_path:
            raise RuntimeError("SENTINEL_DNA_DB_PATH must be configured for production")

        parent = Path(database_path).expanduser().resolve().parent
        if not parent.is_dir() or not os.access(parent, os.W_OK):
            raise RuntimeError("SENTINEL_DNA_DB_PATH must point to a usable database location")
