from __future__ import annotations
from functools import wraps
from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from .playbook_engine import PlaybookEngine
from .repository import AutomationRepository

automation_api = Blueprint("automation_api", __name__, url_prefix="/api/automation")
_repository = AutomationRepository()
def _engine(): return PlaybookEngine(_repository)
def _audit(event, details=None): current_app.container.get("audit_service").record(event, user_id=session.get("user_id"), details=details or {})
def _csrf_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        expected = session.get("csrf_token")
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not expected or supplied != expected: return jsonify({"error": "csrf_validation_failed"}), 403
        return view(*args, **kwargs)
    return wrapped

@automation_api.post("/playbooks")
@permission_required("automation:manage")
@_csrf_required
def create_playbook():
    data = request.get_json(silent=True) or {}
    try: playbook = _engine().create(data.get("name", ""), data.get("steps", []), data.get("description", ""))
    except (TypeError, ValueError): return jsonify({"error": "invalid_playbook"}), 400
    _audit("AUTOMATION_PLAYBOOK_CREATED", {"playbook_id": playbook.id}); return jsonify(playbook.public()), 201

@automation_api.post("/execute")
@permission_required("automation:execute")
@_csrf_required
def execute_playbook():
    data = request.get_json(silent=True) or {}
    try: execution = _engine().execute(data.get("playbook_id", ""), session.get("user_id"), data.get("input", {}))
    except LookupError: return jsonify({"error": "playbook_not_found"}), 404
    except (TypeError, ValueError): return jsonify({"error": "execution_failed"}), 400
    _audit("AUTOMATION_EXECUTED", {"execution_id": execution.id, "playbook_id": execution.playbook_id}); return jsonify(execution.public()), 202

@automation_api.get("/history")
@permission_required("automation:read")
def history(): return jsonify({"executions": [item.public() for item in _repository.history()]})
