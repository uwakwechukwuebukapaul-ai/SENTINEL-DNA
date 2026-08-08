"""
Sentinel DNA Report Repository

Stores generated investigation reports.
"""

from __future__ import annotations

from typing import Any


class ReportRepository:
    """
    Report persistence repository.

    Current:
        In-memory storage.

    Future:
        Database-backed storage.
    """

    def __init__(self) -> None:

        self._reports: dict[
            str,
            dict[str, Any],
        ] = {}

    def create(
        self,
        case_id: str,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create and store investigation report.

        Repository contract used by persistence workflows.
        """

        stored_report = {
            "case_id": case_id,
            "report": report,
        }

        self._reports[case_id] = stored_report

        return stored_report

    def save(
        self,
        case_id: str,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Store investigation report.
        """

        self._reports[case_id] = report

        return report

    def get(
        self,
        case_id: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve report.
        """

        return self._reports.get(
            case_id
        )

    def exists(
        self,
        case_id: str,
    ) -> bool:

        return case_id in self._reports

    def list_all(self) -> list[dict[str, Any]]:
        """
        Return stored reports.
        """

        return list(
            self._reports.values()
        )