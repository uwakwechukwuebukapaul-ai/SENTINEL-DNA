"""
Investigation API Schemas.

Handles request normalization.
"""

from typing import Any


class InvestigationRequest:
    """
    Investigation execution request.
    """

    def __init__(
        self,
        payload: dict[str, Any],
    ) -> None:

        self.case_id = payload.get(
            "case_id"
        )

        self.artifacts = payload.get(
            "artifacts",
            [],
        )


    def validate(self) -> None:
        """
        Validate incoming request.
        """

        if not isinstance(
            self.artifacts,
            list,
        ):
            raise ValueError(
                "artifacts must be a list"
            )


    def to_dict(self) -> dict[str, Any]:

        return {
            "case_id": self.case_id,
            "artifacts": self.artifacts,
        }