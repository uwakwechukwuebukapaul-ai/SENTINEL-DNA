"""Validated production configuration for Sentinel DNA."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ProductionConfig:
    secret_key: str
    database_path: Path
    secure_cookies: bool = True
    testing: bool = False
    database_url: str = ""
    redis_url: str = ""

    @classmethod
    def from_env(cls) -> "ProductionConfig":
        secret = os.getenv("SENTINEL_DNA_SECRET_KEY", "")
        if os.getenv("SENTINEL_DNA_ENV", "development").lower() == "production" and len(secret) < 32:
            raise RuntimeError("SENTINEL_DNA_SECRET_KEY must be at least 32 characters in production")
        database_url = os.getenv("DATABASE_URL", "")
        redis_url = os.getenv("REDIS_URL", "")
        if os.getenv("SENTINEL_DNA_ENV", "development").lower() == "production" and not database_url:
            raise RuntimeError("DATABASE_URL is required in production")
        return cls(secret or "development-only-change-me", Path(os.getenv("SENTINEL_DNA_DB_PATH", "soc.db")).resolve(), os.getenv("SENTINEL_DNA_SECURE_COOKIES", "1") == "1", False, database_url, redis_url)

def validate_startup() -> ProductionConfig:
    return ProductionConfig.from_env()
