from uuid import uuid4
from .models import LessonLearned
class LearningEngine:
    def lessons(self, tenant_id, records):
        if not records: return []
        common=records[0].source; return [LessonLearned(str(uuid4()), tenant_id, f"Review recurring {common} intelligence patterns", f"{len(records)} historical record(s) are available for analyst comparison", [record.record_id for record in records])]
