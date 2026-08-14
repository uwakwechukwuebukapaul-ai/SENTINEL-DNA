from collections import Counter
from .models import UserBehaviorProfile, EntityBehaviorProfile
class BehaviorProfiler:
    def __init__(self, repository): self.repository=repository
    def build(self, organization_id, events):
        grouped={}
        for e in events:
            user=e.user_id or e.normalized_event.get("user", "")
            if user: grouped.setdefault(user, []).append(e)
        result=[]
        for user, rows in grouped.items():
            hours=[str((r.normalized_event or r.raw_event).get("hour")) for r in rows if (r.normalized_event or r.raw_event).get("hour") is not None]
            devices=[(r.normalized_event or r.raw_event).get("device") for r in rows if (r.normalized_event or r.raw_event).get("device")]
            apps=[(r.normalized_event or r.raw_event).get("application") for r in rows if (r.normalized_event or r.raw_event).get("application")]
            item=UserBehaviorProfile(organization_id,user,sorted(set(hours)),[],sorted(set(devices)),sorted(set(apps)),len(rows)); self.repository.profiles.append(item); result.append(item)
        return result
