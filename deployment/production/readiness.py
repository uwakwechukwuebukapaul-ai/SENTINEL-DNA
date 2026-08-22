"""CLI entrypoint for the local production-readiness assessment."""
from __future__ import annotations

import json
from pathlib import Path

from config.runtime import RuntimeConfig
from database.connection import database
from services.core.production_readiness import assess_production_readiness


def build_report() -> dict:
    runtime = RuntimeConfig.from_environment()
    database_ok = False
    try:
        with database.session() as connection:
            connection.execute("SELECT 1").fetchone()
        database_ok = True
    except Exception:
        database_ok = False
    required_services_ok = False
    canonical_authority_ok = False
    request_limits_configured = False
    try:
        from app import create_app

        application = create_app()
        coordinator = application.container.get("investigation_coordinator")
        required_services_ok = all(getattr(coordinator, name, None) is not None for name in (
            "operations_evaluation_repository",
            "operational_notification_repository",
        ))
        canonical_authority_ok = application.container.get("canonical_authority") is not None
        request_limits_configured = bool(application.config.get("MAX_CONTENT_LENGTH"))
    except Exception:
        pass
    return assess_production_readiness(
        environment=runtime.environment,
        secure_cookies=runtime.secure_cookies,
        debug=runtime.debug,
        secret_configured=runtime.environment != "production" or runtime.secret_key != "development-only-secret",
        database_ok=database_ok,
        required_services_ok=required_services_ok,
        canonical_authority_ok=canonical_authority_ok,
        request_limits_configured=request_limits_configured,
        documentation_root=Path(__file__).resolve().parents[2] / "docs",
    )


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2, sort_keys=True))
