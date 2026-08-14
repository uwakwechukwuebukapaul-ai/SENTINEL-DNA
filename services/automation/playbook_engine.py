from __future__ import annotations
from datetime import datetime, timezone
from .action_executor import ActionExecutor
from .models import Execution, Playbook
from .repository import AutomationRepository

class PlaybookEngine:
    def __init__(self, repository=None, executor=None): self.repository = repository or AutomationRepository(); self.executor = executor or ActionExecutor()
    def create(self, name, steps, description=""):
        if not name or not isinstance(steps, list) or not steps: raise ValueError("invalid_playbook")
        for step in steps:
            if not isinstance(step, dict) or "action" not in step: raise ValueError("invalid_playbook_step")
        return self.repository.save_playbook(Playbook(name=name.strip(), steps=steps, description=description))
    def execute(self, playbook_id, actor_id, input_data=None):
        playbook = self.repository.get_playbook(playbook_id)
        if not playbook or not playbook.enabled: raise LookupError("playbook_not_found")
        execution = self.repository.save_execution(Execution(playbook_id, actor_id, input_data or {}))
        for step in playbook.steps:
            execution.results.append(self.executor.execute(step["action"], step.get("parameters", {}), execution.input))
        execution.status = "completed"; execution.approval = "approved"; execution.completed_at = datetime.now(timezone.utc).isoformat()
        return self.repository.save_execution(execution)
