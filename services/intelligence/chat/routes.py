from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
from services.intelligence.feedback import FeedbackStore
from .service import AnalystChatService
chat_api = Blueprint("chat_api", __name__, url_prefix="/api/intelligence/chat")
_chat = AnalystChatService(); _feedback = FeedbackStore()
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
def _org(): return current_organization().organization_id
@chat_api.post("/ask")
@permission_required("copilot:use")
@tenant_required
def ask():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}
    try: result = _chat.ask(_org(), session.get("user_id"), data.get("question", ""), data.get("investigation"))
    except ValueError as exc: return jsonify({"error": str(exc)}), 400
    current_app.container.get("audit_service").record("COPILOT_QUESTION_ANSWERED", user_id=session.get("user_id"), details={"organization_id": _org()}); return jsonify(result)
@chat_api.get("/history")
@permission_required("copilot:read")
@tenant_required
def history(): return jsonify({"conversation": _chat.history(_org())})
@chat_api.post("/feedback")
@permission_required("copilot:use")
@tenant_required
def feedback():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}; outcome = data.get("outcome")
    if outcome not in {"approved", "rejected"}: return jsonify({"error": "invalid_feedback"}), 400
    item = _feedback.record(_org(), session.get("user_id"), data.get("decision_id", ""), outcome, data.get("correction"), data.get("confidence")); current_app.container.get("audit_service").record("COPILOT_FEEDBACK_RECORDED", user_id=session.get("user_id"), details={"organization_id": _org(), "outcome": outcome}); return jsonify(item), 201
@chat_api.get("/metrics")
@permission_required("copilot:read")
@tenant_required
def metrics(): return jsonify(_feedback.metrics(_org()))
@chat_api.post("/replay")
@permission_required("copilot:read")
@tenant_required
def replay(): return jsonify({"timeline": _chat.replay((request.get_json(silent=True) or {}).get("investigation", {}))})
