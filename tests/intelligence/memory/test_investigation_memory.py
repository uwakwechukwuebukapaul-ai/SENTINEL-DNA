from services.intelligence.memory import (
    InvestigationMemory,
)


def test_store_memory():

    memory = InvestigationMemory()

    result = memory.store(
        "INV-001",
        {
            "threat": "phishing"
        },
    )

    assert result["threat"] == "phishing"



def test_retrieve_memory():

    memory = InvestigationMemory()

    memory.store(
        "INV-001",
        {
            "severity": "high"
        },
    )

    result = memory.retrieve(
        "INV-001"
    )

    assert result["severity"] == "high"



def test_memory_exists():

    memory = InvestigationMemory()

    memory.store(
        "INV-001",
        {},
    )

    assert memory.exists(
        "INV-001"
    )



def test_delete_memory():

    memory = InvestigationMemory()

    memory.store(
        "INV-001",
        {},
    )

    assert memory.delete(
        "INV-001"
    )

    assert not memory.exists(
        "INV-001"
    )



def test_clear_memory():

    memory = InvestigationMemory()

    memory.store(
        "INV-001",
        {},
    )

    memory.clear()

    assert memory.list_all() == []