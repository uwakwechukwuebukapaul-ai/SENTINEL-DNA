from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, session

from .case_service import CaseService
from services.auth.permissions import permission_required

cases_api = Blueprint("cases_api", __name__, url_prefix="/api/cases")


def _service() -> CaseService:
    return current_app.container.get("case_service")


def _user_id() -> int:
    return int(session.get("user_id", 0))


@cases_api.post("/<case_id>/assign")
@permission_required("cases:assign")
def assign_case(case_id: str):
    data = request.get_json(silent=True) or {}
    if not data.get("user_id"):
        return jsonify({"error": "user_id_required"}), 400
    return jsonify(_service().assign(case_id, int(data["user_id"]), _user_id() or None))


@cases_api.get("/<case_id>/assignment")
@permission_required("cases:assign")
def get_assignment(case_id: str):
    value = _service().assignment(case_id)
    return jsonify(value or {"error": "assignment_not_found"}), 200 if value else 404


@cases_api.post("/<case_id>/notes")
@permission_required("cases:notes")
def add_note(case_id: str):
    data = request.get_json(silent=True) or {}
    if not _user_id() or not isinstance(data.get("note"), str) or not data["note"].strip():
        return jsonify({"error": "authenticated_note_required"}), 400
    return jsonify(_service().add_note(case_id, _user_id(), data["note"].strip())), 201


@cases_api.get("/<case_id>/notes")
@permission_required("cases:notes")
def get_notes(case_id: str):
    return jsonify({"case_id": case_id, "notes": _service().notes(case_id)})
