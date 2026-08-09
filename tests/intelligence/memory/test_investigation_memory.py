"""
Tests for Investigation Memory Layer.
"""


from services.intelligence.memory import (
    InvestigationMemory,
    MemoryStore,
)



def test_memory_creation():

    memory = InvestigationMemory()

    assert memory is not None



def test_remember_investigation():

    memory = InvestigationMemory()


    result = memory.remember(

        {
            "id":
                "INC-001",

            "type":
                "phishing",

            "severity":
                "critical",

        }

    )


    assert (
        result["id"]
        ==
        "INC-001"
    )



def test_recall_memory():

    memory = InvestigationMemory()


    memory.remember(

        {
            "id":
                "INC-002",

            "type":
                "malware",

        }

    )


    results = memory.recall()


    assert len(results) == 1



def test_find_similar():

    memory = InvestigationMemory()


    memory.remember(

        {
            "id":
                "INC-003",

            "type":
                "phishing",

        }

    )


    result = memory.find_similar(
        "phishing"
    )


    assert (
        result["count"]
        ==
        1
    )



def test_clear_memory():

    memory = InvestigationMemory()


    memory.remember(

        {
            "id":
                "INC-004",

        }

    )


    memory.clear()


    assert (
        memory.size()
        ==
        0
    )



def test_custom_store():

    store = MemoryStore()

    memory = InvestigationMemory(
        store
    )


    memory.remember(
        {
            "id":
                "CUSTOM-1"
        }
    )


    assert (
        memory.size()
        ==
        1
    )