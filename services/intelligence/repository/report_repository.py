"""
Investigation report repository.

Responsible for:
- storing investigation reports
- converting domain objects into JSON-safe structures
- preserving compatibility with existing Sentinel DNA modules
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any


class InvestigationReportRepository:
    """
    Persistent abstraction for investigation reports.

    Legacy contract:
        InvestigationReportRepository.save()
        InvestigationReportRepository.get_all()
        InvestigationReportRepository.clear()

    Supports:
        - dataclasses
        - domain objects
        - dictionaries
        - lists
    """


    def __init__(self):

        self.reports: list[dict[str, Any]] = []



    def _serialize(
        self,
        value: Any,
    ) -> Any:

        if value is None:
            return None


        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value


        if is_dataclass(value):

            return self._serialize(
                asdict(value)
            )


        if hasattr(
            value,
            "to_dict",
        ):

            return self._serialize(
                value.to_dict()
            )


        if hasattr(
            value,
            "__dict__",
        ):

            return {
                key: self._serialize(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }


        if isinstance(
            value,
            dict,
        ):

            return {
                str(key): self._serialize(item)
                for key, item in value.items()
            }


        if isinstance(
            value,
            (list, tuple, set),
        ):

            return [
                self._serialize(item)
                for item in value
            ]


        return str(value)



    def save(
        self,
        report: Any,
    ):

        payload = self._serialize(
            report
        )

        # Validate JSON compatibility
        encoded = json.dumps(
            payload
        )

        stored = json.loads(
            encoded
        )

        self.reports.append(
            stored
        )

        return stored



    def get_all(self):

        return list(
            self.reports
        )



    def all(self):

        return self.get_all()

    def get_by_case_id(self, case_id: str):
        """Return the most recently saved report for a case."""
        for report in reversed(self.reports):
            if isinstance(report, dict) and report.get("case_id") == case_id:
                return report
        return None



    def clear(self):

        self.reports.clear()



# Backward compatibility
ReportRepository = InvestigationReportRepository
