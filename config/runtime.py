"""Environment-aware deployment configuration."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
import secrets
from typing import Mapping

from database.backend import DatabaseConfigurationError, DatabaseSettings


_VALID_ENVIRONMENTS = {"development", "testing", "test", "staging", "production"}
_PRODUCTION_PLACEHOLDERS = {
    "development-only-secret",
    "development-only-change-me",
    "change-me-before-production",
}


def _configured_secret(
    name: str,
    environ: Mapping[str, str] | None = None,
) -> tuple[str, bool]:
    """Read a configured secret directly or from a Docker secret file."""
    values = os.environ if environ is None else environ
    configured = values.get(name)
    if configured is not None:
        return configured, True

    file_name = f"{name}_FILE"
    secret_file = values.get(file_name, "").strip()
    if not secret_file:
        return "", False
    try:
        value = Path(secret_file).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f"{file_name} must point to a readable secret file") from exc
    return value, bool(value)


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
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "RuntimeConfig":
        """Resolve runtime settings from a supplied or process environment."""
        values = os.environ if environ is None else environ
        environment = values.get("SENTINEL_DNA_ENV", values.get("FLASK_ENV", "development")).lower()
        raw_flask_debug = values.get("FLASK_DEBUG", "").strip().lower()
        raw_secure_cookies = values.get("SENTINEL_DNA_SECURE_COOKIES", "").strip()
        raw_pilot_access_required = values.get("SENTINEL_DNA_PILOT_ACCESS_REQUIRED", "").strip()
        debug = environment == "development" or (
            raw_flask_debug in {"1", "true", "yes", "on"}
        )
        configured_database_path = values.get("SENTINEL_DNA_DB_PATH")
        database_path = (
            configured_database_path
            if configured_database_path is not None
            else ("" if environment == "production" else str(Path("soc.db")))
        )
        configured_secret, secret_was_configured = _configured_secret("SENTINEL_DNA_SECRET_KEY", values)
        secret_key = configured_secret if secret_was_configured else (
            "" if environment == "production" else secrets.token_urlsafe(48)
        )
        return cls(
            environment,
            database_path,
            secret_key,
            raw_secure_cookies == "1",
            debug,
            values.get("DATABASE_URL", "").strip(),
            raw_pilot_access_required == "1",
            values.get("SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION", "").strip().lower(),
            values.get("SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION", "").strip().lower(),
            raw_pilot_access_required,
            raw_secure_cookies,
            raw_flask_debug,
            secret_was_configured,
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
        # Validate the resolved configuration, not the ambient process
        # environment. This matters to evidence validators that project an
        # operator-supplied environment without mutating process state.
        database_path = self.database_path.strip()
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
