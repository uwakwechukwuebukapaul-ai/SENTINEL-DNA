from __future__ import annotations
from threading import RLock
from .models import Execution, Playbook

class AutomationRepository:
    """Replaceable repository boundary; v1 keeps state process-local."""
    def __init__(self): self._playbooks: dict[str, Playbook] = {}; self._executions: dict[str, Execution] = {}; self._lock = RLock()
    def save_playbook(self, playbook):
        with self._lock: self._playbooks[playbook.id] = playbook
        return playbook
    def get_playbook(self, playbook_id): return self._playbooks.get(playbook_id)
    def save_execution(self, execution):
        with self._lock: self._executions[execution.id] = execution
        return execution
    def history(self): return list(self._executions.values())
