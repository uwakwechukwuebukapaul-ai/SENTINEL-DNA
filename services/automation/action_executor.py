from __future__ import annotations
from typing import Any, Protocol
from .models import SAFE_ACTIONS

class IntegrationAdapter(Protocol):
    def enrich_ioc(self, value: str, context: dict[str, Any]) -> dict[str, Any]: ...

class ActionExecutor:
    """Safe, side-effect-limited actions. Vendor adapters can be injected later."""
    def execute(self, action: str, parameters: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        if action not in SAFE_ACTIONS: raise ValueError("unsupported_action")
        return {"action": action, "status": "completed", "parameters": parameters, "context": context}
