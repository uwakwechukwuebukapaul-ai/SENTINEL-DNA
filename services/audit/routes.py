"""Authenticated tenant-scoped audit read API."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from database.errors import DatabaseError
from services.auth.permissions import permission_required
from services.core.security_context import request_context
from services.validation.canonical import CanonicalValidationError, normalize_limit


audit_api = Blueprint("audit_api", __name__, url_prefix="/api/admin")


@audit_api.get("/audit")
@permission_required("audit:read")
def list_audit_events():
    context = request_context()
    if context.error or not context.tenant_id:
        return jsonify({"error": "tenant_access_denied"}), 403

    try:
        limit = normalize_limit(request.args.get("limit"), default=50, maximum=100)
    except CanonicalValidationError:
        return jsonify({"error": "invalid_limit"}), 400

    event_type = request.args.get("event_type")
    if event_type is not None and (not event_type.strip() or len(event_type) > 128):
        return jsonify({"error": "invalid_event_type"}), 400

    try:
        service = current_app.container.require("audit_read_service")
        events = service.list_for_tenant(
            context.tenant_id,
            limit=limit,
            event_type=event_type.strip() if event_type else None,
        )
        current_app.container.require("audit_service").record(
            "AUDIT_READ",
            user_id=int(context.user_id) if str(context.user_id).isdigit() else None,
            tenant_id=context.tenant_id,
            actor_id=context.actor_id,
            operation="read",
            outcome="success",
            details={"limit": limit, "event_type": event_type.strip() if event_type else None},
        )
        return jsonify({
            "version": "audit-read-v1",
            "events": events,
            "limit": limit,
            "count": len(events),
        })
    except ValueError as exc:
        if str(exc) in {"invalid_limit", "invalid_event_type", "tenant_context_required"}:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"error": "audit_read_unavailable"}), 503
    except (DatabaseError, LookupError):
        return jsonify({"error": "audit_read_unavailable"}), 503
    except Exception:
        current_app.logger.warning("audit read failed")
        return jsonify({"error": "audit_read_unavailable"}), 503


__all__ = ["audit_api"]
