from __future__ import annotations
from typing import Any, Callable
from .models import ExecutionGraph

class ExecutionGraphExecutor:
    """Deterministic advisory scheduler; it performs no external actions."""
    advisory_only = True

    def execute(self, graph: ExecutionGraph, handler: Callable[[str], Any] | None = None) -> ExecutionGraph:
        completed: set[str] = set()
        remaining = list(graph.nodes)
        while remaining:
            ready = [node for node in remaining if all(dep in completed for dep in node.dependencies)]
            if not ready:
                for node in remaining:
                    node.status, node.result = "blocked", {"error": "dependency_cycle"}
                break
            for node in ready:
                node.status = "running"
                try:
                    node.result = handler(node.name) if handler else {"scheduled": True, "advisory_only": True}
                    node.status = "completed"
                    completed.add(node.name)
                except Exception:
                    node.status, node.result = "failed", {"error": "task_handler_failed"}
                remaining.remove(node)
        return graph
