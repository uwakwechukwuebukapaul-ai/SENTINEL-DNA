from services.intelligence.soc_workspace import SOCWorkspaceService

class SOCAPIService:
    def __init__(self, workspace_service=None): self.workspace=workspace_service or SOCWorkspaceService()
    def _safe(self, fn, *args):
        try:return fn(*args),[]
        except Exception:return None,["workspace_component_unavailable"]
    def get_dashboard(self): return self._safe(getattr(self.workspace, "get_workspace_snapshot", lambda: (_ for _ in ()).throw(AttributeError("workspace snapshot unavailable"))))
    def get_case_view(self, case_id): return self._safe(self.workspace.get_case_workspace,case_id)
    def get_threat_posture(self): return self._safe(self.workspace.get_threat_posture)
    def get_metrics(self): return self._safe(self.workspace.get_investigation_metrics)
