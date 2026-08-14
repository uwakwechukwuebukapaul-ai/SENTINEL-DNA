from typing import Any
from .models import LearningContext

class LearningMemory:
    """Adapter for existing Agent Memory, Investigation Memory, or intelligence memory."""
    def __init__(self, *memories: Any) -> None: self.memories = memories
    def remember(self, context: LearningContext) -> tuple[str, ...]:
        refs = []
        for memory in self.memories:
            method = getattr(memory, "remember", None) or getattr(memory, "store", None) or getattr(memory, "add", None)
            if method:
                result = method(context.to_dict())
                refs.append(str(result) if result is not None else memory.__class__.__name__)
        return tuple(refs)
