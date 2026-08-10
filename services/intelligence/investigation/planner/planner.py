"""
Sentinel DNA Investigation Planner.

Creates structured investigation
workflows from security cases.
"""


from ...models import (
    InvestigationPlan,
    InvestigationTask,
)


class InvestigationPlanner:
    """
    Generates investigation plans.
    """


    DEFAULT_TASKS = [
        {
            "name": "Analyze collected evidence",
            "priority": "high",
            "description": (
                "Review available evidence "
                "associated with the case."
            ),
        },
        {
            "name": "Extract indicators of compromise",
            "priority": "high",
            "description": (
                "Identify IPs, domains, hashes "
                "and suspicious artifacts."
            ),
        },
        {
            "name": "Perform IOC enrichment",
            "priority": "high",
            "description": (
                "Enrich indicators using "
                "threat intelligence sources."
            ),
        },
        {
            "name": "Map MITRE ATT&CK techniques",
            "priority": "medium",
            "description": (
                "Identify attacker behavior "
                "and techniques."
            ),
        },
        {
            "name": "Generate risk assessment",
            "priority": "high",
            "description": (
                "Calculate severity and "
                "investigation confidence."
            ),
        },
    ]


    def create_plan(
        self,
        case_id: str,
        objective: str,
        indicators=None,
    ) -> InvestigationPlan:
        """
        Create investigation workflow.
        """

        plan = InvestigationPlan(
            case_id=case_id,
            objective=objective,
        )


        for task_data in self.DEFAULT_TASKS:

            task = InvestigationTask(
                name=task_data["name"],
                priority=task_data["priority"],
                description=task_data["description"],
            )

            plan.add_task(task)


        if indicators:
            plan.metadata["indicator_count"] = len(
                indicators
            )


        plan.metadata["planner"] = (
            "Sentinel DNA Investigation Planner"
        )


        return plan