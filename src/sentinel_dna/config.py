"""Central, environment-based runtime configuration for the beta deployment."""
from dataclasses import dataclass
import os
import base64
import json
from pathlib import Path


@dataclass(frozen=True)
class SentinelDNASettings:
    data_dir: str = "data"
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = False
    environment: str = "development"
    saas_database_url: str | None = None
    redis_url: str | None = None
    secret_backend: str = "environment"
    encryption_key: str | None = None
    rate_limit_per_minute: int = 0
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_ids: dict[str, str] | None = None
    metrics_private: bool = False
    metrics_token: str | None = None

    @classmethod
    def from_environment(cls) -> "SentinelDNASettings":
        port = int(os.getenv("SENTINEL_DNA_PORT", "5000"))
        if not 1 <= port <= 65535:
            raise ValueError("SENTINEL_DNA_PORT must be between 1 and 65535")
        environment = os.getenv("SENTINEL_DNA_ENV", "development").lower()
        if environment not in {"development", "test", "production"}:
            raise ValueError("SENTINEL_DNA_ENV must be development, test, or production")
        debug = os.getenv("SENTINEL_DNA_DEBUG", "false").lower() == "true"
        database_url = os.getenv("SENTINEL_DNA_SAAS_DATABASE_URL") or None
        redis_url = os.getenv("SENTINEL_DNA_REDIS_URL") or None
        secret_backend = os.getenv("SENTINEL_DNA_SECRET_BACKEND", "environment").lower()
        encryption_key = os.getenv("SENTINEL_DNA_ENCRYPTION_KEY") or None
        rate_limit_per_minute = int(os.getenv("SENTINEL_DNA_RATE_LIMIT_PER_MINUTE", "0"))
        stripe_secret_key = os.getenv("STRIPE_SECRET_KEY") or None
        stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET") or None
        stripe_price_ids_raw = os.getenv("STRIPE_PRICE_IDS") or None
        metrics_private = os.getenv("SENTINEL_DNA_METRICS_PRIVATE", "false").lower() == "true"
        metrics_token = os.getenv("SENTINEL_DNA_METRICS_TOKEN") or None
        stripe_price_ids = None
        if stripe_price_ids_raw:
            try:
                stripe_price_ids = json.loads(stripe_price_ids_raw)
            except json.JSONDecodeError:
                raise ValueError("STRIPE_PRICE_IDS must be a JSON object") from None
            if not isinstance(stripe_price_ids, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in stripe_price_ids.items()):
                raise ValueError("STRIPE_PRICE_IDS must map plan IDs to Stripe price IDs")
        if secret_backend not in {"environment", "external"}:
            raise ValueError("SENTINEL_DNA_SECRET_BACKEND must be environment or external")
        if database_url and not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("SENTINEL_DNA_SAAS_DATABASE_URL must be a PostgreSQL URL")
        if redis_url and not redis_url.startswith(("redis://", "rediss://")):
            raise ValueError("SENTINEL_DNA_REDIS_URL must be a Redis URL")
        if rate_limit_per_minute < 0:
            raise ValueError("SENTINEL_DNA_RATE_LIMIT_PER_MINUTE must not be negative")
        if any([stripe_secret_key, stripe_webhook_secret, stripe_price_ids]) and not all([stripe_secret_key, stripe_webhook_secret, stripe_price_ids]):
            raise ValueError("Stripe configuration requires STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, and STRIPE_PRICE_IDS")
        if environment == "production":
            if debug:
                raise ValueError("SENTINEL_DNA_DEBUG must be false in production")
            if not database_url:
                raise ValueError("SENTINEL_DNA_SAAS_DATABASE_URL is required in production")
            if secret_backend == "environment" and not encryption_key:
                raise ValueError("SENTINEL_DNA_ENCRYPTION_KEY is required when using environment secrets in production")
            if rate_limit_per_minute == 0:
                raise ValueError("SENTINEL_DNA_RATE_LIMIT_PER_MINUTE is required in production")
            if any([stripe_secret_key, stripe_webhook_secret, stripe_price_ids]) and not all([stripe_secret_key, stripe_webhook_secret, stripe_price_ids]):
                raise ValueError("complete Stripe configuration is required when Stripe is enabled")
            if metrics_private and not metrics_token:
                raise ValueError("SENTINEL_DNA_METRICS_TOKEN is required when private metrics are enabled")
        if encryption_key:
            try:
                if len(base64.urlsafe_b64decode(encryption_key.encode("ascii"))) != 32:
                    raise ValueError
            except (ValueError, UnicodeEncodeError):
                raise ValueError("SENTINEL_DNA_ENCRYPTION_KEY must be a base64-encoded 32-byte key") from None
        return cls(
            data_dir=os.getenv("SENTINEL_DNA_DATA_DIR", "data"),
            host=os.getenv("SENTINEL_DNA_HOST", "127.0.0.1"),
            port=port,
            debug=debug,
            environment=environment,
            saas_database_url=database_url,
            redis_url=redis_url,
            secret_backend=secret_backend,
            encryption_key=encryption_key,
            rate_limit_per_minute=rate_limit_per_minute,
            stripe_secret_key=stripe_secret_key,
            stripe_webhook_secret=stripe_webhook_secret,
            stripe_price_ids=stripe_price_ids,
            metrics_private=metrics_private,
            metrics_token=metrics_token,
        )

    def ensure_data_dir(self) -> Path:
        path = Path(self.data_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
