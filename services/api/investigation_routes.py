"""
Sentinel DNA Investigation API Routes

Enterprise investigation API boundary.

Flow:

API Request
    |
    v
Investigation Coordinator
    |
    v
Agent Pipeline
    |
    v
Runtime Executor
    |
    v
AI Agents
    |
    v
Intelligence Layer
    |
    v
AI Report Generation
    |
    v
Report Storage
"""

from __future__ import annotations

from typing import Any

from services.core.serialization import serialize

from flask import Blueprint
from flask import jsonify
from flask import request


from services.intelligence.orchestration.investigation_coordinator import (
    InvestigationCoordinator,
)

from services.intelligence.agents.agent_registry import (
    AgentRegistry,
)

from services.intelligence.runtime.runtime_task_executor import (
    RuntimeTaskExecutor,
)

from services.intelligence.agents.bootstrap import (
    bootstrap_agents,
)

from services.intelligence.agents.runtime_adapter import (
    AgentRuntimeAdapter,
)

from services.intelligence.reporting.intelligent_report_service import (
    IntelligentReportService,
)

from services.intelligence.reporting.report_storage import (
    ReportStorage,
)


# ============================================================
# Blueprint
# ============================================================

investigation_bp = Blueprint(
    "investigation",
    __name__,
    url_prefix="/api/investigations",
)


# ============================================================
# Runtime Initialization
# ============================================================

agent_registry = AgentRegistry()

runtime_executor = RuntimeTaskExecutor()

runtime_adapter = AgentRuntimeAdapter(
    runtime_executor,
)


bootstrap_agents(
    agent_registry,
    runtime_adapter=runtime_adapter,
)


investigation_coordinator = InvestigationCoordinator(
    registry=agent_registry,
    runtime=runtime_executor,
)


report_service = IntelligentReportService()

report_storage = ReportStorage()


# ============================================================
# Serialization
# ============================================================

def _serialize(value):

    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, list):
        return [
            _serialize(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            key: _serialize(item)
            for key, item in value.items()
        }

    if hasattr(value, "value"):
        return value.value

    return serialize(value)


# ============================================================
# Generate Investigation Report
# ============================================================

@investigation_bp.route(
    "/report",
    methods=["POST"],
)
def generate_investigation_report():

    payload: dict[str, Any] = (
        request.get_json(
            silent=True
        )
        or {}
    )


    case_id = payload.get(
        "case_id"
    )

    alert = payload.get(
        "alert"
    )


    if not case_id:

        return jsonify(
            {
                "success": False,
                "error": "case_id is required",
            }
        ), 400


    if not isinstance(
        alert,
        dict,
    ):

        return jsonify(
            {
                "success": False,
                "error": "alert must be an object",
            }
        ), 400


    try:

        orchestration_result = (
            investigation_coordinator.investigate(
                case_id=case_id,
                alert=alert,
            )
        )


        artifacts = [

            {
                "type": "ioc",
                "value": alert.get(
                    "indicator"
                ),
            },

            {
                "type": "alert",
                "value": alert,
            },

        ]


        report = (
            report_service.generate(
                case_id=case_id,
                orchestration_result=(
                    orchestration_result
                ),
                artifacts=artifacts,
            )
        )


        report = _serialize(
            report
        )


        report_storage.save_report(
            case_id=case_id,
            report=report,
        )


        return jsonify(
            {
                "success": True,
                "report": report,
            }
        ), 200


    except Exception as error:

        import traceback

        traceback.print_exc()

        return jsonify(
            {
                "success": False,
                "error": str(error),
            }
        ), 500



# ============================================================
# Retrieve Investigation Report
# ============================================================

@investigation_bp.route(
    "/report/<case_id>",
    methods=["GET"],
)
def get_investigation_report(
    case_id: str,
):

    try:

        report = (
            report_storage.get_report(
                case_id
            )
        )


        if report is None:

            return jsonify(
                {
                    "success": False,
                    "error": "Report not found",
                }
            ), 404


        return jsonify(
            {
                "success": True,
                "report": _serialize(
                    report
                ),
            }
        ), 200


    except Exception as error:

        return jsonify(
            {
                "success": False,
                "error": str(error),
            }
        ), 500
