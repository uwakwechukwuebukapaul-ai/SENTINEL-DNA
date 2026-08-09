"""
Memory storage engine.

Initial implementation uses
in-memory storage.

Designed for future replacement with:
- SQLite
- PostgreSQL
- Vector Database
- Knowledge Graph
"""


from typing import Any


class MemoryStore:
    """
    Generic investigation memory storage.
    """


    def __init__(self):

        self.records: list[dict[str, Any]] = []



    def save(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Store memory record.
        """

        self.records.append(
            record
        )

        return record



    def get_all(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return all stored memories.
        """

        return self.records.copy()



    def find(
        self,
        key: str,
        value: Any,
    ) -> list[dict[str, Any]]:
        """
        Search memory records.
        """

        results = []


        for record in self.records:

            if record.get(key) == value:

                results.append(
                    record
                )


        return results



    def clear(
        self,
    ) -> None:
        """
        Remove all memory.
        """

        self.records.clear()



    def count(
        self,
    ) -> int:

        return len(
            self.records
        )