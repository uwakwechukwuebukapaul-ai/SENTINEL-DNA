"""
Sentinel DNA Case Repository Adapter.

Provides dashboard access to investigation cases.

Keeps dashboard layer independent from
case management implementation.
"""

from __future__ import annotations

from typing import Any


class CaseRepositoryAdapter:
    """
    Adapter between dashboard and case services.
    """


    def __init__(
        self,
        case_manager=None,
    ) -> None:

        self.case_manager = case_manager



    def get(
        self,
        case_id: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve case information.
        """


        if self.case_manager is None:
            return None


        if hasattr(
            self.case_manager,
            "get_case",
        ):

            return self.case_manager.get_case(
                case_id
            )


        if hasattr(
            self.case_manager,
            "get",
        ):

            return self.case_manager.get(
                case_id
            )


        return None