class WorkspaceTimeline:
    def render(self,events):
        return sorted([x.to_dict() if hasattr(x,"to_dict") else dict(x) for x in (events or [])],key=lambda x:str(x.get("timestamp",x.get("created_at",""))))
