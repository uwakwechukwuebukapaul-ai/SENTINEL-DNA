"""
Tests for Investigation Orchestrator.
"""

from services.intelligence.orchestration import (
    InvestigationOrchestrator,
    WorkflowState,
)



class FakeInvestigator:


    def investigate(
        self,
        case_id,
        artifacts,
    ):

        return {

            "analysis": {

                "risk":
                    "high"

            },

            "case_id":
                case_id,

        }



class FakeExecution:


    def execute(
        self,
        investigation,
    ):

        return {

            "action":
                "contain"

        }



class FakeReporter:


    def build(
        self,
        case_id,
        orchestration_result,
    ):

        return {

            "case_id":
                case_id,

            "status":
                "completed",

        }



def create_orchestrator():

    return InvestigationOrchestrator(

        investigator=FakeInvestigator(),

        execution_engine=FakeExecution(),

        reporter=FakeReporter(),

    )



def test_orchestrator_initialization():

    engine = create_orchestrator()

    assert engine.state.status() == "created"



def test_investigation_execution():

    engine = create_orchestrator()


    result = engine.investigate(

        case_id="CASE-001",

        artifacts=[
            {
                "type": "ioc",
                "value": "evil.com",
            }
        ],

    )


    assert result["case_id"] == "CASE-001"

    assert result["status"] == "completed"



def test_investigator_result():

    engine = create_orchestrator()


    result = engine.investigate(

        case_id="CASE-002",

    )


    assert (
        result["investigation"]["analysis"]["risk"]
        ==
        "high"
    )



def test_execution_result():

    engine = create_orchestrator()


    result = engine.investigate(

        case_id="CASE-003",

    )


    assert (
        result["execution"]["action"]
        ==
        "contain"
    )



def test_report_result():

    engine = create_orchestrator()


    result = engine.investigate(

        case_id="CASE-004",

    )


    assert (
        result["report"]["status"]
        ==
        "completed"
    )



def test_workflow_failure():

    class Broken:

        def investigate(
            self,
            case_id,
            artifacts,
        ):

            raise Exception(
                "failed"
            )


    engine = InvestigationOrchestrator(

        investigator=Broken()

    )


    result = engine.investigate(

        case_id="CASE-005",

    )


    assert result["status"] == "failed"