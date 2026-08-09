"""
Investigation Memory Intelligence.

Provides learning context from previous investigations.
"""


from typing import Any

from .memory_store import MemoryStore



class InvestigationMemory:
    """
    Memory interface for AI investigations.
    """


    def __init__(
        self,
        store: MemoryStore | None = None,
    ):

        self.store = (
            store
            or MemoryStore()
        )



    def remember(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Save investigation knowledge.
        """

        return self.store.save(
            investigation
        )



    def recall(
        self,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all investigations.
        """

        return self.store.get_all()



    def find_similar(
        self,
        investigation_type: str,
    ) -> dict[str, Any]:
        """
        Find previous similar investigations.
        """


        matches = self.store.find(
            "type",
            investigation_type,
        )


        return {

            "query":
                investigation_type,

            "matches":
                matches,

            "count":
                len(matches),

        }



    def clear(
        self,
    ):

        self.store.clear()



    def size(
        self,
    ) -> int:

        return self.store.count()