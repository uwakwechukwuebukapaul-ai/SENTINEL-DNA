"""Validated production configuration for Sentinel DNA."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

from .runtime import RuntimeConfig

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
        runtime = RuntimeConfig.from_environment()
        runtime.validate()
        database_url = os.getenv("DATABASE_URL", "")
        redis_url = os.getenv("REDIS_URL", "")
        return cls(
            runtime.secret_key,
            Path(runtime.database_path).expanduser().resolve(),
            runtime.secure_cookies,
            runtime.debug,
            database_url,
            redis_url,
        )

def validate_startup() -> ProductionConfig:
    return ProductionConfig.from_env()
