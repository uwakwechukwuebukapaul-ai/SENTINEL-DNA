"""
Tests Intelligence Coordinator
"""

from services.intelligence.investigation.intelligence_coordinator import (
    IntelligenceCoordinator,
)



class FakeResult:

    status = "completed"

    findings = {
        "analysis_engine": {
            "confidence": 0.9
        }
    }



class FakeService:

    def investigate(
        self,
        case_id,
        alert,
    ):

        return FakeResult()



class FakeReasoner:

    def analyze(
        self,
        data,
    ):

        return {
            "summary":
                "credential phishing detected"
        }



class FakeMitre:

    def map_artifact(
        self,
        artifact,
    ):

        return [
            {
                "technique_id":
                    "T1566"
            }
        ]



def test_intelligence_analysis():

    coordinator = IntelligenceCoordinator(
        investigation_service=
            FakeService(),

        reasoner=
            FakeReasoner(),

        mitre_mapper=
            FakeMitre(),
    )


    result = coordinator.analyze(
        case_id="CASE-900",
        alert={
            "source":
                "email"
        },
    )


    assert (
        result["case_id"]
        ==
        "CASE-900"
    )


    assert (
        result["investigation"]["status"]
        ==
        "completed"
    )


    assert (
        result["reasoning"]["summary"]
        ==
        "credential phishing detected"
    )


    assert (
        result["mitre"][0]["technique_id"]
        ==
        "T1566"
    )