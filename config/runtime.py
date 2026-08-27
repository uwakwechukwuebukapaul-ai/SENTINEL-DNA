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
    pilot_access_required: bool = False
    config_source_classification: str = ""
    database_target_classification: str = ""
    raw_pilot_access_required: str = ""
    raw_secure_cookies: str = ""
    raw_flask_debug: str = ""
    secret_was_configured: bool = False

    @classmethod
    def from_environment(cls) -> "RuntimeConfig":
        environment = os.getenv("SENTINEL_DNA_ENV", os.getenv("FLASK_ENV", "development")).lower()
        raw_flask_debug = os.getenv("FLASK_DEBUG", "").strip().lower()
        raw_secure_cookies = os.getenv("SENTINEL_DNA_SECURE_COOKIES", "").strip()
        raw_pilot_access_required = os.getenv("SENTINEL_DNA_PILOT_ACCESS_REQUIRED", "").strip()
        debug = environment == "development" or (
            raw_flask_debug in {"1", "true", "yes", "on"}
        )
        configured_secret = os.getenv("SENTINEL_DNA_SECRET_KEY")
        secret_key = configured_secret if configured_secret is not None else (
            "" if environment == "production" else secrets.token_urlsafe(48)
        )
        return cls(
            environment,
            os.getenv("SENTINEL_DNA_DB_PATH", str(Path("soc.db"))),
            secret_key,
            raw_secure_cookies == "1",
            debug,
            os.getenv("DATABASE_URL", "").strip(),
            raw_pilot_access_required == "1",
            os.getenv("SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION", "").strip().lower(),
            os.getenv("SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION", "").strip().lower(),
            raw_pilot_access_required,
            raw_secure_cookies,
            raw_flask_debug,
            configured_secret is not None,
        )

    def validate(self) -> None:
        if self.environment not in _VALID_ENVIRONMENTS:
            raise RuntimeError("SENTINEL_DNA_ENV must be a supported environment")

        if self.environment == "staging":
            self._validate_staging()
            return

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

    def _validate_staging(self) -> None:
        """Validate the isolated, pilot-gated staging runtime contract."""
        if self.raw_pilot_access_required != "1":
            raise RuntimeError(
                "SENTINEL_DNA_PILOT_ACCESS_REQUIRED must be exactly 1 for staging"
            )
        if self.raw_secure_cookies != "1":
            raise RuntimeError(
                "SENTINEL_DNA_SECURE_COOKIES must be exactly 1 for staging"
            )
        if self.raw_flask_debug != "0":
            raise RuntimeError("FLASK_DEBUG must be exactly 0 for staging")
        if not self.secret_was_configured or not self._valid_secret():
            raise RuntimeError(
                "SENTINEL_DNA_SECRET_KEY must be a non-placeholder staging secret"
            )
        if self.config_source_classification != "external_non_production":
            raise RuntimeError(
                "SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION must be external_non_production"
            )
        if self.database_target_classification != "disposable_staging":
            raise RuntimeError(
                "SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION must be disposable_staging"
            )

        if not self.database_url:
            raise RuntimeError(
                "DATABASE_URL must be configured with a disposable PostgreSQL URL for staging"
            )
        try:
            DatabaseSettings.from_environment(
                database_url=self.database_url,
                require_postgresql=True,
            )
        except DatabaseConfigurationError as exc:
            raise RuntimeError(str(exc)) from exc

    def _valid_secret(self) -> bool:
        value = self.secret_key.strip()
        lowered = value.lower()
        return bool(
            len(value) >= 32
            and lowered not in _PRODUCTION_PLACEHOLDERS
            and "change-me" not in lowered
            and "replace-with" not in lowered
            and "inject_" not in lowered
            and "__" not in value
        )
