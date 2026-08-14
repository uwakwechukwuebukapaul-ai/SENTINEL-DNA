from __future__ import annotations
from typing import Any
from .models import ExecutionGraph, ExecutionNode

class ExecutionGraphBuilder:
    """Translate plans into an advisory dependency graph."""
    def build(self, plan: Any) -> ExecutionGraph:
        tasks = list(getattr(plan, "tasks", []) or plan.get("tasks", []))
        case_id = getattr(plan, "case_id", None) or plan.get("case_id", "")
        priority = getattr(plan, "priority", None) or plan.get("priority", "medium")
        nodes = []
        previous = None
        for task in tasks:
            name = str(task)
            nodes.append(ExecutionNode(name=name, priority=priority, dependencies=[previous] if previous else []))
            previous = name
        return ExecutionGraph(case_id=case_id, nodes=nodes)
