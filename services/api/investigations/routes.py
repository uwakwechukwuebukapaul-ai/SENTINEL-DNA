"""Stable REST endpoints for Sentinel DNA investigations."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from .schemas import investigation_request, investigation_response


investigations_api = Blueprint("investigations_api", __name__, url_prefix="/api/investigations")


def _coordinator():
    return current_app.container.get("investigation_coordinator")


@investigations_api.post("")
def create_investigation():
    case_id, alert, artifacts, error = investigation_request(request.get_json(silent=True))
    if error:
        return jsonify({"error": error}), 400
    result = _coordinator().investigate(case_id=case_id, alert=alert, artifacts=artifacts)
    return jsonify(investigation_response(result)), 200


@investigations_api.get("/<case_id>")
def get_investigation(case_id: str):
    coordinator = _coordinator()
    intelligence = coordinator.intelligence_repository.get_by_case_id(case_id)
    report = coordinator.get_report_by_case_id(case_id)
    if intelligence is None and report is None:
        return jsonify({"error": "investigation_not_found"}), 404
    return jsonify({
        "case_id": case_id,
        "intelligence": intelligence,
        "timeline": (intelligence or {}).get("timeline", []),
        "report": report,
        "metadata": (intelligence or {}).get("metadata", {}),
    })


@investigations_api.get("/<case_id>/report")
def get_investigation_report(case_id: str):
    report = _coordinator().get_report_by_case_id(case_id)
    if report is None:
        return jsonify({"error": "report_not_found"}), 404
    return jsonify(report)


@investigations_api.get("/<case_id>/timeline")
def get_investigation_timeline(case_id: str):
    intelligence = _coordinator().intelligence_repository.get_by_case_id(case_id)
    if intelligence is None:
        return jsonify({"error": "investigation_not_found"}), 404
    return jsonify({"case_id": case_id, "timeline": intelligence.get("timeline", [])})
