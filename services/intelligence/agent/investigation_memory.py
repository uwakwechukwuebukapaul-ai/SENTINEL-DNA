"""
Investigation Memory.

Stores investigation history
for autonomous reasoning.
"""

from __future__ import annotations

from typing import Any



class InvestigationMemory:
    """
    Temporary investigation memory store.
    """

    def __init__(self):

        self.memory: dict[
            str,
            list[dict[str, Any]]
        ] = {}



    def remember(
        self,
        case_id: str,
        data: dict[str, Any],
    ) -> None:
        """
        Store investigation information.
        """

        self.memory.setdefault(
            case_id,
            [],
        )

        self.memory[case_id].append(
            data
        )



    def recall(
        self,
        case_id: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve investigation memory.
        """

        return self.memory.get(
            case_id,
            [],
        ).copy()



    def clear(
        self,
        case_id: str | None = None,
    ) -> None:
        """
        Clear memory.
        """

        if case_id:

            self.memory.pop(
                case_id,
                None,
            )

        else:

            self.memory.clear()