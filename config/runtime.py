"""Environment-aware deployment configuration."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

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
        return cls(environment, os.getenv("SENTINEL_DNA_DB_PATH", str(Path("soc.db"))), os.getenv("SENTINEL_DNA_SECRET_KEY", "development-only-secret"), os.getenv("SENTINEL_DNA_SECURE_COOKIES", "0") == "1", environment == "development")

    def validate(self) -> None:
        if self.environment != "production":
            return

        if len(self.secret_key) < 32 or self.secret_key == "development-only-secret":
            raise RuntimeError("SENTINEL_DNA_SECRET_KEY must be configured for production")

        if not self.secure_cookies:
            raise RuntimeError("SENTINEL_DNA_SECURE_COOKIES must be enabled for production")

        database_path = os.getenv("SENTINEL_DNA_DB_PATH")
        if not database_path:
            raise RuntimeError("SENTINEL_DNA_DB_PATH must be configured for production")

        parent = Path(database_path).expanduser().resolve().parent
        if not parent.is_dir():
            raise RuntimeError("SENTINEL_DNA_DB_PATH must point to a usable database location")
