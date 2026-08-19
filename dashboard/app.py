"""Sentinel DNA SOC Command Center dashboard."""
from __future__ import annotations

import os
import sqlite3
import logging
import re
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_from_directory,
    Response,
    session,
)

from jinja2 import ChoiceLoader, FileSystemLoader


# Core platform services
from database.connection import resolve_database_path
from services.core.application_container import build_container
from services.api.investigations.controller import InvestigationController

# Authentication / authorization
from services.auth import auth_api
from services.auth.security import csrf_token
from services.auth.permissions import permission_required

# Case management
from services.cases import cases_api

# Investigation APIs
from services.api.investigations import investigations_api

# Dashboard
from services.dashboard.dashboard_service import (
    DashboardService as CommandCenterDashboardService
)

# Intelligence
from services.intelligence.copilot import InvestigationCopilot
from services.intelligence.reasoning import reasoning_api
from services.intelligence.chat import chat_api
from services.intelligence.investigation_decision import create_investigation_decision_blueprint
from services.intelligence.investigation_learning.routes import create_investigation_learning_blueprint

# Security services
from services.observability import ObservabilityService
from services.tenancy.context import tenant_required

# Feature modules
from services.hunting import hunting_api, HuntRepository
from services.automation import automation_api
from services.integrations import integrations_api
from services.detection import detection_api
from services.adversary import adversary_api

from services.validation import validation_api
from services.tenancy import tenancy_api
from services.connectors import connectors_api
from services.streaming import streaming_api

from services.governance.routes import governance_api
from services.marketplace.routes import marketplace_api
from services.incidents.routes import incidents_api
from services.api_management.routes import api_management_api
from services.billing.routes import billing_api

from services.mssp.routes import mssp_api
from services.compliance.routes import compliance_api
from services.mlops.routes import mlops_api
from services.monitoring.routes import monitoring_api

from services.customer_success.routes import customer_success_api
from services.product_analytics.routes import product_analytics_api

from services.pilot_reports.routes import pilot_reports_api
from services.pilot_management.routes import pilot_management_api

from services.support.routes import support_api
from services.exercises.routes import exercise_api
from services.readiness.routes import readiness_api

from services.customer_zero import customer_zero_api
from services.customer_zero.demo_routes import demo_api

from services.detection.content.routes import content_api

from services.intelligence.threat.routes import threat_api
from services.intelligence.feeds.routes import feeds_api

from services.exposure.routes import exposure_api
from services.data_lake.routes import data_api

from services.analytics.ueba.routes import ueba_api

from services.ai_agents.routes import agent_api
from services.graph.routes import graph_api
from services.query_engine.routes import query_api

from services.xdr.routes import xdr_api
from services.autonomous_hunting.routes import hunting_ai_api

from services.security_twin.routes import twin_api

from services.prevention.routes import prevention_api
from services.security_validation.routes import validation_ai_api

from services.security_memory.routes import memory_api

from services.soc_manager.routes import soc_api
from services.security_advisor.routes import advisor_api

from lab.lab_content.routes import lab_api

from services.operations_hardening.routes import ops_api
from services.pilot_simulation.routes import pilot_api

from services.identity_security.routes import identity_api
from services.data_security.routes import data_security_api

from services.decision_intelligence.routes import decision_api

from services.security_copilot.routes import copilot_ai_api

from services.platform_experience.routes import experience_api



# ---------------------------------------------------------
# BASE CONFIGURATION
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = resolve_database_path()


app = Flask(
    __name__,
    template_folder="templates"
)


app.jinja_loader = ChoiceLoader(
    [
        app.jinja_loader,
        FileSystemLoader(
            str(
                BASE_DIR /
                "dashboard" /
                "workspace" /
                "templates"
            )
        ),
    ]
)


app.secret_key = os.getenv(
    "SENTINEL_DNA_SECRET_KEY",
    "development-only-change-me"
)


app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(
        os.getenv(
            "SENTINEL_DNA_SECURE_COOKIES",
            "0"
        ) == "1"
    )
)


app.config["JSON_SORT_KEYS"] = False

app.config["OBSERVABILITY"] = ObservabilityService()

app.config["HUNT_DB_PATH"] = str(DB_PATH)



# ---------------------------------------------------------
# APPLICATION CONTAINER
# ---------------------------------------------------------

app.container = build_container()



# ---------------------------------------------------------
# BLUEPRINT REGISTRATION
# ---------------------------------------------------------

app.register_blueprint(investigations_api)
app.register_blueprint(create_investigation_decision_blueprint())
app.register_blueprint(create_investigation_learning_blueprint())
from dashboard.analyst_workspace import analyst_workspace
app.register_blueprint(analyst_workspace)
app.register_blueprint(auth_api)
app.register_blueprint(cases_api)

app.register_blueprint(hunting_api)
app.register_blueprint(automation_api)
app.register_blueprint(integrations_api)

app.register_blueprint(detection_api)
app.register_blueprint(adversary_api)
app.register_blueprint(validation_api)

app.register_blueprint(tenancy_api)
app.register_blueprint(connectors_api)

app.register_blueprint(streaming_api)

app.register_blueprint(reasoning_api)
app.register_blueprint(chat_api)

app.register_blueprint(governance_api)
app.register_blueprint(marketplace_api)

app.register_blueprint(incidents_api)
app.register_blueprint(api_management_api)

app.register_blueprint(billing_api)

app.register_blueprint(mssp_api)
app.register_blueprint(compliance_api)

app.register_blueprint(mlops_api)
app.register_blueprint(monitoring_api)

app.register_blueprint(customer_success_api)

app.register_blueprint(product_analytics_api)

app.register_blueprint(
    pilot_reports_api
)

app.register_blueprint(
    pilot_management_api
)

app.register_blueprint(
    support_api
)

app.register_blueprint(
    exercise_api
)

app.register_blueprint(
    readiness_api
)

app.register_blueprint(
    customer_zero_api
)

app.register_blueprint(
    content_api
)

app.register_blueprint(
    threat_api
)

app.register_blueprint(
    feeds_api
)

app.register_blueprint(
    exposure_api
)

app.register_blueprint(
    data_api
)

app.register_blueprint(
    ueba_api
)

app.register_blueprint(
    agent_api
)

app.register_blueprint(
    graph_api
)

app.register_blueprint(
    query_api
)

app.register_blueprint(
    xdr_api
)

app.register_blueprint(
    hunting_ai_api
)

app.register_blueprint(
    twin_api
)

app.register_blueprint(
    prevention_api
)

app.register_blueprint(
    validation_ai_api
)

app.register_blueprint(
    memory_api
)

app.register_blueprint(
    soc_api
)

app.register_blueprint(
    advisor_api
)

app.register_blueprint(
    lab_api
)

app.register_blueprint(
    demo_api
)

app.register_blueprint(
    ops_api
)

app.register_blueprint(
    pilot_api
)

app.register_blueprint(
    identity_api
)

app.register_blueprint(
    data_security_api
)

app.register_blueprint(
    decision_api
)

app.register_blueprint(
    copilot_ai_api
)

app.register_blueprint(
    experience_api
)


logger = logging.getLogger(
    "sentinel_dna.dashboard"
)

# ---------------------------------------------------------
# SECURITY HEADERS + REQUEST OBSERVABILITY
# ---------------------------------------------------------

DIAGNOSTIC_VERSION = "dashboard-production-v2"


@app.after_request
def add_security_headers(response):

    response.headers["X-Sentinel-App-File"] = __file__
    response.headers["X-Sentinel-App-PID"] = str(os.getpid())
    response.headers["X-Sentinel-App-Diagnostic"] = DIAGNOSTIC_VERSION

    response.headers["X-Frame-Options"] = "DENY"

    response.headers["X-Content-Type-Options"] = "nosniff"

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'"
    )

    app.config["OBSERVABILITY"].event(
        "api_request",
        method=request.method,
        path=request.path,
        status=response.status_code,
    )

    return response


@app.before_request
def enforce_csrf():
    if request.method in {
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    }:

        if request.endpoint in {
            "auth_api.register",
            "auth_api.login",
            "run_investigation",
            "investigations_api.create_investigation",
            "investigations_api.run_investigation_compatibility",
        }:
            return None


        expected = session.get(
            "csrf_token"
        )

        supplied = (
            request.headers.get(
                "X-CSRF-Token"
            )
            or request.form.get(
                "csrf_token"
            )
        )


        if (
            not expected
            or not supplied
            or supplied != expected
        ):
            return jsonify(
                {
                    "error":
                    "csrf_validation_failed"
                }
            ), 403


    if "csrf_token" not in session:
        session["csrf_token"] = csrf_token()


    return None


# ---------------------------------------------------------
# DATABASE HELPERS
# ---------------------------------------------------------

def fetch_all(
    sql: str,
    params: tuple = ()
) -> list[dict]:

    with sqlite3.connect(DB_PATH) as conn:

        conn.row_factory = sqlite3.Row

        return [
            dict(row)
            for row in conn.execute(
                sql,
                params
            ).fetchall()
        ]



def fetch_one(
    sql: str,
    params: tuple = ()
) -> dict:

    rows = fetch_all(
        sql,
        params
    )

    return rows[0] if rows else {}



# ---------------------------------------------------------
# MAIN DASHBOARD PAYLOAD
# ---------------------------------------------------------

def dashboard_payload() -> dict:

    stats = fetch_one(
        """
        SELECT

        (
            SELECT COUNT(*)
            FROM cases
        ) AS cases,


        (
            SELECT COUNT(*)
            FROM evidence
        ) AS evidence,


        (
            SELECT COUNT(*)
            FROM timeline
        ) AS timeline,


        (
            SELECT COUNT(*)
            FROM iocs
        ) AS iocs,


        (
            SELECT COUNT(*)
            FROM cases
            WHERE UPPER(severity)
            IN ('CRITICAL','HIGH')
        ) AS high_risk_cases,


        (
            SELECT COUNT(*)
            FROM cases
            WHERE UPPER(status)
            IN (
                'OPEN',
                'ACTIVE',
                'INVESTIGATING',
                'IN_PROGRESS'
            )
        ) AS active_cases

        """
    )



    cases = fetch_all(
        """
        SELECT

            case_id,
            title,
            severity,
            status,
            analyst,
            created

        FROM cases

        ORDER BY id DESC

        LIMIT 12
        """
    )



    # FIXED IOC QUERY
    iocs = fetch_all(
        """
        SELECT

            case_id,
            ioc_type,
            value,
            created

        FROM iocs

        ORDER BY id DESC

        LIMIT 12
        """
    )



    evidence = fetch_all(
        """
        SELECT

            case_id,
            type,
            data,
            created

        FROM evidence

        ORDER BY id DESC

        LIMIT 8
        """
    )



    timeline = fetch_all(
        """
        SELECT

            case_id,
            event_type,
            description,
            actor,
            created

        FROM timeline

        ORDER BY id DESC

        LIMIT 10
        """
    )



    actions = fetch_all(
        """
        SELECT

            case_id,
            action,
            analyst,
            created

        FROM analyst_actions

        ORDER BY id DESC

        LIMIT 8
        """
    )



    notes = fetch_all(
        """
        SELECT

            case_id,
            note,
            analyst,
            created

        FROM case_notes

        ORDER BY id DESC

        LIMIT 8
        """
    )



    return {

        "stats": stats,

        "cases": cases,

        "iocs": iocs,

        "evidence": evidence,

        "timeline": timeline,

        "actions": actions,

        "notes": notes,

    }



# ---------------------------------------------------------
# DASHBOARD ROUTES
# ---------------------------------------------------------

@app.get("/")
def dashboard():

    return render_template(
        "dashboard.html",
        **dashboard_payload()
    )



@app.get("/api/dashboard")
def dashboard_api():

    return jsonify(
        dashboard_payload()
    )



@app.get("/workspace")
def workspace_home():

    return render_template(
        "dashboard.html",
        **dashboard_payload()
    )



@app.get("/workspace/static/<path:filename>")
def workspace_static(filename):

    return send_from_directory(
        BASE_DIR /
        "dashboard" /
        "workspace" /
        "static",
        filename
    )



@app.get("/workspace/iocs")
def workspace_iocs():

    return render_template(
        "iocs.html",
        iocs=fetch_all(
            """
            SELECT

                case_id,
                ioc_type AS type,
                value,
                created

            FROM iocs

            ORDER BY id DESC
            """
        )
    )

# ---------------------------------------------------------
# ERROR HANDLING
# ---------------------------------------------------------

@app.errorhandler(sqlite3.Error)
def database_error(error):

    logger.exception(
        "dashboard_database_error",
        exc_info=error
    )

    return render_template(
        "error.html",
        message="Dashboard data is temporarily unavailable."
    ), 503



# ---------------------------------------------------------
# SOC COMMAND CENTER DASHBOARD
# ---------------------------------------------------------

@app.get("/workspace/dashboard")
@permission_required("investigations:read")
def workspace_dashboard():

    user_id = session.get(
        "user_id"
    )

    if not user_id:
        return jsonify(
            {
                "error":
                "authentication_required"
            }
        ), 401


    snapshot = CommandCenterDashboardService(
        DB_PATH
    ).snapshot()


    app.container.get(
        "audit_service"
    ).record(
        "DASHBOARD_VIEW",
        user_id=user_id
    )


    return render_template(
        "workspace_dashboard.html",
        snapshot=snapshot
    )


@app.get("/workspace/executive-learning")
@permission_required("investigations:read")
def executive_learning_dashboard():
    return render_template("executive_learning.html")


@app.get("/workspace/maturity")
@permission_required("investigations:read")
def maturity_dashboard():
    return render_template("maturity.html")


@app.get("/workspace/improvement-progress")
@permission_required("investigations:read")
def improvement_progress_dashboard():
    return render_template("improvement_progress.html")

@app.get("/workspace/executive-strategy")
@permission_required("investigations:read")
def executive_strategy_dashboard():
    return render_template("executive_strategy.html")

@app.get("/workspace/executive-strategy/scenarios")
@permission_required("investigations:read")
def executive_scenario_dashboard():
    return render_template("executive_scenario.html")

@app.get("/workspace/executive-strategy/decision-matrix")
@permission_required("investigations:read")
def decision_matrix_dashboard():
    return render_template("decision_matrix.html")

@app.get("/workspace/executive-strategy/planning")
@permission_required("investigations:read")
def strategic_planning_dashboard():
    return render_template("executive_planning.html")

@app.get("/workspace/executive-strategy/planning/analytics")
@permission_required("investigations:read")
def strategic_planning_analytics_dashboard():
    return render_template("executive_planning_analytics.html")

@app.get("/workspace/executive-strategy/planning/effectiveness")
@permission_required("investigations:read")
def strategic_effectiveness_dashboard():
    return render_template("executive_effectiveness.html")

@app.get("/workspace/executive-strategy/portfolio")
@permission_required("investigations:read")
def strategic_portfolio_dashboard():
    return render_template("executive_portfolio.html")

@app.get("/workspace/executive-strategy/portfolio-command-center")
@permission_required("investigations:read")
def portfolio_command_center_dashboard():
    return render_template("executive_portfolio_command_center.html")

@app.get("/workspace/executive-strategy/portfolio-forecast")
@permission_required("investigations:read")
def portfolio_forecast_dashboard():
    return render_template("executive_portfolio_forecast.html")

@app.get("/workspace/executive-strategy/portfolio-forecast/accuracy")
@permission_required("investigations:read")
def portfolio_forecast_accuracy_dashboard():
    return render_template("executive_portfolio_forecast_accuracy.html")

@app.get("/workspace/executive-strategy/portfolio-forecast/governance")
@permission_required("investigations:read")
def portfolio_forecast_governance_dashboard():
    return render_template("executive_portfolio_forecast_governance.html")

@app.get("/workspace/executive-strategy/portfolio-forecast/policy-review")
@permission_required("investigations:read")
def portfolio_forecast_policy_review_dashboard():
    return render_template("executive_portfolio_forecast_policy_review.html")

@app.get("/workspace/executive-strategy/portfolio-forecast/decision-oversight")
@permission_required("investigations:read")
def portfolio_forecast_decision_oversight_dashboard():
    return render_template("executive_portfolio_forecast_decision_oversight.html")

@app.get("/workspace/executive-strategy/portfolio-forecast/policy-analytics")
@permission_required("investigations:read")
def portfolio_forecast_policy_analytics_dashboard():
    return render_template("executive_portfolio_forecast_policy_analytics.html")

@app.get("/workspace/executive-strategy/portfolio-forecast/decision-readiness")
@permission_required("investigations:read")
def portfolio_forecast_decision_readiness_dashboard():
    return render_template("executive_portfolio_forecast_decision_readiness.html")

@app.get("/workspace/executive-strategy/portfolio-forecast/decision-readiness/analytics")
@permission_required("investigations:read")
def portfolio_forecast_decision_readiness_analytics_dashboard():
    return render_template("executive_portfolio_forecast_decision_readiness_analytics.html")

@app.get("/workspace/executive-strategy/portfolio-forecast/governance-command-center")
@permission_required("investigations:read")
def portfolio_forecast_governance_command_center_dashboard():
    return render_template("executive_portfolio_forecast_governance_command_center.html")

@app.get("/workspace/executive-strategy/portfolio-forecast/early-warning")
@permission_required("investigations:read")
def portfolio_forecast_early_warning_dashboard():
    return render_template("executive_portfolio_forecast_early_warning.html")

@app.get("/workspace/executive-strategy/portfolio-forecast/governance-history")
@permission_required("investigations:read")
def portfolio_forecast_governance_history_dashboard():
    return render_template("executive_portfolio_forecast_governance_history.html")

@app.get("/workspace/executive-strategy/portfolio-forecast/intervention-intelligence")
@permission_required("investigations:read")
def portfolio_forecast_intervention_intelligence_dashboard(): return render_template("executive_portfolio_forecast_intervention_intelligence.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/warning-escalation")
@permission_required("investigations:read")
def portfolio_forecast_warning_escalation_dashboard(): return render_template("executive_portfolio_forecast_warning_escalation.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/strategic-risk-coordination")
@permission_required("investigations:read")
def portfolio_forecast_strategic_risk_coordination_dashboard(): return render_template("executive_portfolio_forecast_strategic_risk_coordination.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/intervention-priority")
@permission_required("investigations:read")
def portfolio_forecast_intervention_priority_dashboard(): return render_template("executive_portfolio_forecast_intervention_priority.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/intervention-governance")
@permission_required("investigations:read")
def portfolio_forecast_intervention_governance_dashboard(): return render_template("executive_portfolio_forecast_intervention_governance.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/escalation-lifecycle")
@permission_required("investigations:read")
def portfolio_forecast_escalation_lifecycle_dashboard(): return render_template("executive_portfolio_forecast_escalation_lifecycle.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/risk-response-planning")
@permission_required("investigations:read")
def portfolio_forecast_risk_response_planning_dashboard(): return render_template("executive_portfolio_forecast_risk_response_planning.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/intervention-readiness")
@permission_required("investigations:read")
def portfolio_forecast_intervention_readiness_dashboard(): return render_template("executive_portfolio_forecast_intervention_readiness.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/intervention-command-center")
@permission_required("investigations:read")
def portfolio_forecast_intervention_command_center_dashboard(): return render_template("executive_portfolio_forecast_intervention_command_center.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/escalation-monitoring")
@permission_required("investigations:read")
def portfolio_forecast_escalation_monitoring_dashboard(): return render_template("executive_portfolio_forecast_escalation_monitoring.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/response-effectiveness")
@permission_required("investigations:read")
def portfolio_forecast_response_effectiveness_dashboard(): return render_template("executive_portfolio_forecast_response_effectiveness.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/intervention-governance/trends")
@permission_required("investigations:read")
def portfolio_forecast_intervention_governance_trends_dashboard(): return render_template("executive_portfolio_forecast_intervention_governance_trends.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/intervention-effectiveness")
@permission_required("investigations:read")
def portfolio_forecast_intervention_effectiveness_dashboard(): return render_template("executive_portfolio_forecast_intervention_effectiveness.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/response-outcomes")
@permission_required("investigations:read")
def portfolio_forecast_response_outcomes_dashboard(): return render_template("executive_portfolio_forecast_response_outcomes.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/governance-learning")
@permission_required("investigations:read")
def portfolio_forecast_governance_learning_dashboard(): return render_template("executive_portfolio_forecast_governance_learning.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/governance-learning-command-center")
@permission_required("investigations:read")
def portfolio_forecast_governance_learning_command_center_dashboard(): return render_template("executive_portfolio_forecast_governance_learning_command_center.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/response-monitoring")
@permission_required("investigations:read")
def portfolio_forecast_response_monitoring_dashboard(): return render_template("executive_portfolio_forecast_response_monitoring.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/intervention-strategy-analytics")
@permission_required("investigations:read")
def portfolio_forecast_intervention_strategy_analytics_dashboard(): return render_template("executive_portfolio_forecast_intervention_strategy_analytics.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/governance-learning/trends")
@permission_required("investigations:read")
def portfolio_forecast_governance_learning_trends_dashboard(): return render_template("executive_portfolio_forecast_governance_learning_trends.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/governance-learning/trends/analytics")
@permission_required("investigations:read")
def portfolio_forecast_governance_learning_trends_analytics_dashboard(): return render_template("executive_portfolio_forecast_governance_learning_trends_analytics.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/response-outcome-correlation")
@permission_required("investigations:read")
def portfolio_forecast_response_outcome_correlation_dashboard(): return render_template("executive_portfolio_forecast_response_outcome_correlation.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/improvement-portfolio-analytics")
@permission_required("investigations:read")
def portfolio_forecast_improvement_portfolio_analytics_dashboard(): return render_template("executive_portfolio_forecast_improvement_portfolio_analytics.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/improvement-command-center")
@permission_required("investigations:read")
def portfolio_forecast_improvement_command_center_dashboard(): return render_template("executive_portfolio_forecast_improvement_command_center.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/governance-learning/correlation")
@permission_required("investigations:read")
def portfolio_forecast_governance_learning_correlation_dashboard(): return render_template("executive_portfolio_forecast_governance_learning_correlation.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/response-outcome/trends")
@permission_required("investigations:read")
def portfolio_forecast_response_outcome_trends_dashboard(): return render_template("executive_portfolio_forecast_response_outcome_trends.html")
@app.get("/workspace/executive-strategy/portfolio-forecast/improvement-governance")
@permission_required("investigations:read")
def portfolio_forecast_improvement_governance_dashboard(): return render_template("executive_portfolio_forecast_phase3550.html", endpoint="improvement-governance", title="Improvement portfolio governance", payload_key="governance")
@app.get("/workspace/executive-strategy/portfolio-forecast/outcome-learning")
@permission_required("investigations:read")
def portfolio_forecast_outcome_learning_dashboard(): return render_template("executive_portfolio_forecast_phase3550.html", endpoint="outcome-learning", title="Outcome learning intelligence", payload_key="outcome_learning")
@app.get("/workspace/executive-strategy/portfolio-forecast/continuous-improvement")
@permission_required("investigations:read")
def portfolio_forecast_continuous_improvement_dashboard(): return render_template("executive_portfolio_forecast_phase3550.html", endpoint="continuous-improvement", title="Continuous improvement", payload_key="continuous_improvement")
@app.get("/workspace/executive-strategy/portfolio-forecast/improvement-trends")
@permission_required("investigations:read")
def portfolio_forecast_improvement_trends_dashboard(): return render_template("executive_portfolio_forecast_phase3550.html", endpoint="improvement-trends", title="Longitudinal improvement trends", payload_key="trends")
@app.get("/workspace/executive-strategy/portfolio-forecast/strategic-evolution")
@permission_required("investigations:read")
def portfolio_forecast_strategic_evolution_dashboard(): return render_template("executive_portfolio_forecast_phase3551.html", endpoint="strategic-evolution", title="Strategic evolution intelligence", payload_key="evolution")
@app.get("/workspace/executive-strategy/portfolio-forecast/improvement-maturity")
@permission_required("investigations:read")
def portfolio_forecast_improvement_maturity_dashboard(): return render_template("executive_portfolio_forecast_phase3551.html", endpoint="improvement-maturity", title="Improvement maturity posture", payload_key="maturity")
@app.get("/workspace/executive-strategy/portfolio-forecast/strategic-evolution-command-center")
@permission_required("investigations:read")
def portfolio_forecast_strategic_evolution_command_center_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="strategic-evolution-command-center", title="Strategic evolution command center", payload_key="command_center")
@app.get("/workspace/executive-strategy/portfolio-forecast/governance-optimization-analytics")
@permission_required("investigations:read")
def portfolio_forecast_governance_optimization_analytics_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="governance-optimization-analytics", title="Governance optimization analytics", payload_key="analytics")
@app.get("/workspace/executive-strategy/portfolio-forecast/improvement-maturity-analytics")
@permission_required("investigations:read")
def portfolio_forecast_improvement_maturity_analytics_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="improvement-maturity-analytics", title="Improvement maturity analytics", payload_key="analytics")
@app.get("/workspace/executive-strategy/portfolio-forecast/strategic-evolution-trends")
@permission_required("investigations:read")
def portfolio_forecast_strategic_evolution_trends_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="strategic-evolution-trends", title="Strategic evolution trends", payload_key="trends")
@app.get("/workspace/executive-strategy/intelligence-command-center")
@permission_required("investigations:read")
def executive_intelligence_command_center_dashboard(): return render_template("executive_intelligence_command_center.html")
@app.get("/workspace/executive-strategy/governance-intelligence-monitoring")
@permission_required("investigations:read")
def governance_intelligence_monitoring_dashboard(): return render_template("governance_intelligence_monitoring.html")
@app.get("/workspace/executive-strategy/decision-intelligence-analytics")
@permission_required("investigations:read")
def decision_intelligence_analytics_dashboard(): return render_template("decision_intelligence_analytics.html")
@app.get("/workspace/executive-strategy/operating-model-analytics")
@permission_required("investigations:read")
def operating_model_analytics_dashboard(): return render_template("operating_model_analytics.html")
@app.get("/workspace/executive-strategy/organizational-decision-intelligence")
@permission_required("investigations:read")
def organizational_decision_intelligence_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="organizational-decision-intelligence", title="Organizational decision intelligence", payload_key="profile")
@app.get("/workspace/executive-strategy/strategic-intelligence-health")
@permission_required("investigations:read")
def strategic_intelligence_health_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="strategic-intelligence-health", title="Strategic intelligence health", payload_key="health")
@app.get("/workspace/executive-strategy/executive-intelligence-summary")
@permission_required("investigations:read")
def executive_intelligence_summary_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="executive-intelligence-summary", title="Executive intelligence summary", payload_key="summary")
@app.get("/workspace/executive-strategy/intelligence-operating-model")
@permission_required("investigations:read")
def intelligence_operating_model_dashboard(): return render_template("intelligence_operating_model.html")
@app.get("/workspace/executive-strategy/strategic-portfolio-governance")
@permission_required("investigations:read")
def strategic_portfolio_governance_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="strategic-portfolio-governance", title="Strategic portfolio governance", payload_key="governance")
@app.get("/workspace/executive-strategy/organizational-ai-maturity")
@permission_required("investigations:read")
def organizational_ai_maturity_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="organizational-ai-maturity", title="Organizational AI maturity", payload_key="maturity")
@app.get("/workspace/executive-strategy/intelligence-adoption")
@permission_required("investigations:read")
def intelligence_adoption_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="intelligence-adoption", title="Intelligence adoption analytics", payload_key="adoption")
@app.get("/workspace/executive-strategy/executive-governance-summary")
@permission_required("investigations:read")
def executive_governance_summary_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="executive-governance-summary", title="Executive governance summary", payload_key="summary")
@app.get("/workspace/executive-strategy/intelligence-governance-platform")
@permission_required("investigations:read")
def intelligence_governance_platform_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="intelligence-governance-platform", title="Executive intelligence governance platform", payload_key="platform")
@app.get("/workspace/executive-strategy/decision-lifecycle")
@permission_required("investigations:read")
def decision_lifecycle_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="decision-lifecycle", title="Strategic decision lifecycle", payload_key="lifecycle")
@app.get("/workspace/executive-strategy/organizational-intelligence-evolution")
@permission_required("investigations:read")
def organizational_intelligence_evolution_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="organizational-intelligence-evolution", title="Organizational intelligence evolution", payload_key="evolution")
@app.get("/workspace/executive-strategy/intelligence-feedback-loop")
@permission_required("investigations:read")
def intelligence_feedback_loop_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="intelligence-feedback-loop", title="Intelligence feedback loop", payload_key="feedback")
@app.get("/workspace/executive-strategy/intelligence-evolution-summary")
@permission_required("investigations:read")
def intelligence_evolution_summary_dashboard(): return render_template("executive_portfolio_forecast_phase3552.html", endpoint="intelligence-evolution-summary", title="Executive intelligence evolution summary", payload_key="summary")
@app.get("/workspace/executive-strategy/intelligence-operating-system")
@permission_required("investigations:read")
def intelligence_operating_system_dashboard(): return render_template("executive_intelligence_operating_system.html")
@app.get("/workspace/data-fabric")
@permission_required("analytics:view")
def data_fabric_dashboard(): return render_template("data_fabric_overview.html")
@app.get("/workspace/data-fabric/sources")
@permission_required("analytics:view")
def data_fabric_sources_dashboard(): return render_template("data_fabric_sources.html")
@app.get("/workspace/data-fabric/quality")
@permission_required("analytics:view")
def data_fabric_quality_dashboard(): return render_template("data_fabric_quality.html")
@app.get("/workspace/detection-intelligence/overview")
@permission_required("analytics:view")
def detection_intelligence_overview_dashboard(): return render_template("detection_intelligence.html", title="Detection Intelligence Overview", endpoint="overview")
@app.get("/workspace/detection-intelligence/coverage")
@permission_required("analytics:view")
def detection_intelligence_coverage_dashboard(): return render_template("detection_intelligence.html", title="Detection Coverage Intelligence", endpoint="coverage")
@app.get("/workspace/detection-intelligence/quality")
@permission_required("analytics:view")
def detection_intelligence_quality_dashboard(): return render_template("detection_intelligence.html", title="Detection Quality Intelligence", endpoint="quality")
@app.get("/workspace/detection-intelligence/gaps")
@permission_required("analytics:view")
def detection_intelligence_gaps_dashboard(): return render_template("detection_intelligence.html", title="Detection Gap Intelligence", endpoint="gaps")
@app.get("/workspace/hunting-intelligence/overview")
@permission_required("hunting:read")
def hunting_intelligence_overview_dashboard(): return render_template("hunting_intelligence.html", title="Hunting Intelligence Overview", endpoint="overview")
@app.get("/workspace/hunting-intelligence/prioritization")
@permission_required("hunting:read")
def hunting_intelligence_prioritization_dashboard(): return render_template("hunting_intelligence.html", title="Hunt Prioritization", endpoint="prioritization")
@app.get("/workspace/hunting-intelligence/effectiveness")
@permission_required("hunting:read")
def hunting_intelligence_effectiveness_dashboard(): return render_template("hunting_intelligence.html", title="Hunt Effectiveness", endpoint="effectiveness")
@app.get("/workspace/hunting-intelligence/gaps")
@permission_required("hunting:read")
def hunting_intelligence_gaps_dashboard(): return render_template("hunting_intelligence.html", title="Hunt Gap Analysis", endpoint="gaps")
@app.get("/workspace/copilot")
@permission_required("copilot:view")
def governed_copilot_dashboard(): return render_template("copilot_foundation.html")
@app.get("/workspace/investigation-intelligence")
@permission_required("investigations:read")
def investigation_intelligence_dashboard(): return render_template("investigation_intelligence.html")
@app.get("/workspace/investigation-lifecycle")
@permission_required("investigations:read")
def investigation_lifecycle_dashboard(): return render_template("investigation_lifecycle.html")
@app.get("/workspace/investigation-decision")
@permission_required("investigations:read")
def investigation_decision_dashboard(): return render_template("investigation_decision.html")
@app.get("/workspace/investigation-learning")
@permission_required("investigations:read")
def investigation_learning_dashboard(): return render_template("investigation_learning.html")
@app.get("/workspace/investigation-knowledge")
@permission_required("investigations:read")
def investigation_knowledge_dashboard(): return render_template("investigation_knowledge.html")
@app.get("/workspace/investigation-workflow")
@permission_required("investigations:read")
def investigation_workflow_dashboard(): return render_template("investigation_workflow.html")
@app.get("/workspace/executive-strategy/governance-intelligence-foundation")
@permission_required("investigations:read")
def governance_intelligence_foundation_dashboard(): return render_template("governance_intelligence_foundation.html")
@app.get("/workspace/executive-strategy/decision-intelligence-foundation")
@permission_required("investigations:read")
def decision_intelligence_foundation_dashboard(): return render_template("decision_intelligence_foundation.html")



@app.get("/workspace/dashboard/data")
def workspace_dashboard_data():

    if not session.get("user_id"):

        return jsonify(
            {
                "error":
                "authentication_required"
            }
        ), 401


    snapshot = CommandCenterDashboardService(
        DB_PATH
    ).snapshot()


    return jsonify(
        snapshot.as_dict()
    )



@app.get("/workspace/dashboard/static/<path:filename>")
def dashboard_static(filename):

    return send_from_directory(
        BASE_DIR /
        "dashboard" /
        "static",
        filename
    )



# ---------------------------------------------------------
# CASE API
# ---------------------------------------------------------

@app.get("/api/cases/<case_id>")
def case_api(case_id: str):

    try:

        case = fetch_one(
            """
            SELECT *

            FROM cases

            WHERE case_id=?
            """,
            (case_id,)
        )


        if not case:

            return jsonify(
                {
                    "error":
                    "case_not_found"
                }
            ), 404



        case["evidence"] = fetch_all(
            """
            SELECT

                id,
                type,
                data,
                sha256,
                created

            FROM evidence

            WHERE case_id=?

            ORDER BY id DESC

            """,
            (case_id,)
        )



        # FIXED IOC COLUMN
        case["iocs"] = fetch_all(
            """
            SELECT

                id,
                ioc_id,
                ioc_type,
                value,
                confidence,
                reputation,
                source,
                created

            FROM iocs

            WHERE case_id=?

            ORDER BY id DESC

            """,
            (case_id,)
        )



        case["notes"] = fetch_all(
            """
            SELECT

                id,
                analyst,
                note,
                created

            FROM case_notes

            WHERE case_id=?

            ORDER BY id DESC

            """,
            (case_id,)
        )



        case["timeline"] = fetch_all(
            """
            SELECT

                id,
                event_type,
                description,
                actor,
                created

            FROM timeline

            WHERE case_id=?

            ORDER BY id DESC

            """,
            (case_id,)
        )



        case["actions"] = fetch_all(
            """
            SELECT

                id,
                action,
                analyst,
                created

            FROM analyst_actions

            WHERE case_id=?

            ORDER BY id DESC

            """,
            (case_id,)
        )


        return jsonify(case)



    except Exception:

        logger.exception(
            "CASE API FAILURE case_id=%s",
            case_id
        )


        return render_template(
            "error.html",
            message="Dashboard data is temporarily unavailable."
        ),503



# ---------------------------------------------------------
# AI INVESTIGATION EXECUTION
# ---------------------------------------------------------

@app.post("/api/investigations/run")
def run_investigation():

    payload = request.get_json(
        silent=True
    ) or {}


    case_id = payload.get(
        "case_id"
    )


    if not isinstance(
        case_id,
        str
    ) or not case_id.strip():

        return jsonify(
            {
                "error":
                "case_id_required"
            }
        ),400



    case = fetch_one(
        """
        SELECT

            case_id,
            title,
            severity,
            description,
            status

        FROM cases

        WHERE case_id=?

        """,
        (case_id,)
    )


    if not case:

        return jsonify(
            {
                "error":
                "case_not_found"
            }
        ),404



    evidence = fetch_all(
        """
        SELECT

            id,
            type,
            data,
            sha256,
            created

        FROM evidence

        WHERE case_id=?

        ORDER BY id

        """,
        (case_id,)
    )



    artifacts = [

        {
            "type": row["type"],
            "data": row["data"],
            "created": row["created"]
        }

        for row in evidence

    ]



    iocs = fetch_all(
        """
        SELECT

            id,
            ioc_type AS type,
            value,
            created

        FROM iocs

        WHERE case_id=?

        ORDER BY id

        """,
        (case_id,)
    )



    timeline = fetch_all(
        """
        SELECT

            id,
            event_type,
            description,
            actor,
            created

        FROM timeline

        WHERE case_id=?

        ORDER BY id

        """,
        (case_id,)
    )



    alert = {

        "case_id":
        case_id,

        "title":
        case["title"],

        "severity":
        case["severity"],

        "description":
        case["description"]

    }



    result = InvestigationController(
        app.container.get(
            "investigation_coordinator"
        )
    ).run(
        artifacts,
        case_id,
        alert,
        evidence=evidence,
        iocs=iocs,
        timeline=timeline
    )


    return jsonify(result)



# ---------------------------------------------------------
# HEALTH + READINESS
# ---------------------------------------------------------

@app.get("/healthz")
def healthz():

    try:

        fetch_one(
            "SELECT 1 AS ok"
        )


        return jsonify(
            {
                "status":"ok",
                "service":
                "sentinel-dna-dashboard"
            }
        )


    except sqlite3.Error:


        return jsonify(
            {
                "status":
                "degraded"
            }
        ),503



@app.get("/readyz")
def readyz():

    return healthz()



@app.get("/health")
def health():

    return jsonify(
        {
            "status":
            "ok",

            "service":
            "sentinel-dna",

            "database":
            "configured"
        }
    )



@app.get("/ready")
def ready():

    try:

        fetch_one(
            "SELECT 1 AS ok"
        )


        return jsonify(
            {
                "status":
                "ready",

                "database":
                "ok",

                "services":
                {
                    "investigation":
                    "configured",

                    "observability":
                    "configured"
                }
            }
        )


    except sqlite3.Error:

        return jsonify(
            {
                "status":
                "not_ready",

                "database":
                "unavailable"
            }
        ),503



# ---------------------------------------------------------
# APPLICATION START
# ---------------------------------------------------------

if __name__ == "__main__":

    app.run(
        host=os.getenv(
            "SENTINEL_DNA_HOST",
            "127.0.0.1"
        ),

        port=int(
            os.getenv(
                "SENTINEL_DNA_PORT",
                "5000"
            )
        ),

        debug=False
    )
