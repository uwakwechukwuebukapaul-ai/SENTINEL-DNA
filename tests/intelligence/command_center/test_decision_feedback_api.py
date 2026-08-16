from services.domain_contracts import FeedbackOutcome
from services.identity.compatibility import CanonicalIdentityContext
from services.intelligence.command_center.api import create_command_center_blueprint
from services.intelligence.command_center.decision import DecisionContext
from services.intelligence.command_center.decision_repository import DecisionContextRepository
from services.intelligence.feedback.store import FeedbackStore
from services.domain_contracts import DecisionFeedbackWriteBoundary
from services.tenant.authorization import TenantAuthorizationService


def test_command_center_decision_feedback_route_uses_injected_boundary():
    decisions = DecisionContextRepository()
    decisions.save(DecisionContext("decision-1", "tenant-1"))
    store = FeedbackStore()
    boundary = DecisionFeedbackWriteBoundary(
        decisions,
        store,
        lambda tenant: "org-1",
        TenantAuthorizationService(),
    )
    blueprint = create_command_center_blueprint(
        tenant_resolver=lambda: "tenant-1",
        decision_feedback_boundary=boundary,
        identity_context_resolver=lambda tenant, payload: CanonicalIdentityContext(
            tenant_id=tenant,
            actor_id="user-1",
            role="analyst",
            authorization_scope=("investigations.read",),
        ),
    )

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(blueprint)

    response = app.test_client().post(
        "/api/command-center/decision/decision-1/feedback",
        json={"outcome": FeedbackOutcome.APPROVED.value, "confidence": .8},
    )

    assert response.status_code == 201
    assert response.get_json()["tenant_id"] == "tenant-1"
    assert response.get_json()["user_id"] == "user-1"
    assert store.list("org-1")[0]["decision_id"] == "decision-1"


def test_command_center_decision_feedback_route_has_no_implicit_fallback():
    blueprint = create_command_center_blueprint(tenant_resolver=lambda: "tenant-1")
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(blueprint)

    response = app.test_client().post(
        "/api/command-center/decision/decision-1/feedback",
        json={"outcome": "approved"},
    )

    assert response.status_code == 503
    assert response.get_json()["error"] == "decision_feedback_unavailable"


def test_command_center_decision_feedback_route_rejects_malformed_outcome():
    blueprint = create_command_center_blueprint(
        tenant_resolver=lambda: "tenant-1",
        decision_feedback_boundary=object(),
        identity_context_resolver=lambda tenant, payload: CanonicalIdentityContext(
            tenant_id=tenant,
            actor_id="user-1",
            role="analyst",
            authorization_scope=("investigations.read",),
        ),
    )
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(blueprint)

    response = app.test_client().post(
        "/api/command-center/decision/decision-1/feedback",
        json={"outcome": "not-a-feedback-outcome"},
    )

    assert response.status_code == 400
