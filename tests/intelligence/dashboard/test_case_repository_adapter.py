"""
Case Repository Adapter Tests.
"""

from services.intelligence.dashboard.adapters.case_repository_adapter import (
    CaseRepositoryAdapter,
)



class FakeCaseManager:


    def get_case(
        self,
        case_id,
    ):

        return {

            "case_id": case_id,

            "status": "completed",

        }



def test_adapter_creation():

    adapter = CaseRepositoryAdapter()

    assert adapter is not None



def test_adapter_get_case():

    adapter = CaseRepositoryAdapter(
        FakeCaseManager()
    )


    result = adapter.get(
        "CASE-001"
    )


    assert result["case_id"] == "CASE-001"



def test_adapter_missing_manager():

    adapter = CaseRepositoryAdapter()


    result = adapter.get(
        "CASE-001"
    )


    assert result is None