from __future__ import annotations
from abc import ABC, abstractmethod
from collections import defaultdict
from .models import DetectionFeedback

class DetectionFeedbackRepository(ABC):
    @abstractmethod
    def save(self, feedback: DetectionFeedback) -> DetectionFeedback: ...
    @abstractmethod
    def list(self, detection_id: str | None = None, tenant_id: str | None = None) -> list[DetectionFeedback]: ...

class InMemoryDetectionFeedbackRepository(DetectionFeedbackRepository):
    def __init__(self) -> None: self._items: dict[tuple[str | None, str], list[DetectionFeedback]] = defaultdict(list)
    def save(self, feedback: DetectionFeedback) -> DetectionFeedback:
        self._items[(feedback.tenant_id, feedback.detection_id)].append(feedback)
        return feedback
    def list(self, detection_id: str | None = None, tenant_id: str | None = None) -> list[DetectionFeedback]:
        return [item for (item_tenant, item_detection), values in self._items.items() if (detection_id is None or item_detection == detection_id) and (tenant_id is None or item_tenant == tenant_id) for item in values]
    def list_feedback(self, tenant_id: str | None = None) -> list[DetectionFeedback]:
        return self.list(tenant_id=tenant_id)
