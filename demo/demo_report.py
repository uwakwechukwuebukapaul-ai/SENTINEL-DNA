"""
Sentinel DNA Demo Report Generator

Formats investigation simulation
results into analyst-friendly output.
"""

from __future__ import annotations

from datetime import datetime
import json



class DemoReport:
    """
    Converts investigation results
    into readable SOC reports.
    """


    def generate(
        self,
        result: dict,
    ) -> str:
        """
        Generate formatted investigation report.
        """


        scenario = result.get(
            "scenario",
            "unknown"
        )


        status = result.get(
            "status",
            "unknown"
        )


        execution = result.get(
            "execution",
            {}
        )


        execution = self._serialize(
            execution
        )


        return f"""
==================================================
 Sentinel DNA AI Investigation Report
==================================================

Generated:
{datetime.utcnow().isoformat()} UTC


Scenario:
{scenario}


Status:
{status}


Execution Details:

{json.dumps(
    execution,
    indent=4
)}


==================================================
 End of Investigation Report
==================================================
"""


    def _serialize(
        self,
        value,
    ):
        """
        Convert internal objects into
        JSON-compatible structures.
        """


        if value is None:

            return None



        if isinstance(
            value,
            dict
        ):

            return {
                key: self._serialize(
                    item
                )
                for key, item in value.items()
            }



        if isinstance(
            value,
            list
        ):

            return [
                self._serialize(
                    item
                )
                for item in value
            ]



        if hasattr(
            value,
            "__dict__"
        ):

            return {
                key: self._serialize(
                    item
                )
                for key, item in value.__dict__.items()
                if not key.startswith("_")
            }



        return value